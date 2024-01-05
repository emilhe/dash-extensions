import json
import dash
from collections import OrderedDict
from typing import Optional, Any
from dash import html, Input, Output, State, clientside_callback
from dash.development.base_component import Component

"""
This module holds utilities related to the [Dash pages](https://dash.plotly.com/urls).
"""

_ID_CONTENT = "_component_content"
_COMPONENT_PATH_REGISTRY = OrderedDict()
_PROP_PATH_REGISTRY = OrderedDict()
_CONTAINER_REGISTRY = {}
_COMPONENT_CONTAINER = html.Div(id=_ID_CONTENT, disable_n_clicks=True)

# region Monkey patch page registration function

_original_register_page = dash.register_page


def _register_page(*args, dynamic_components=None, dynamic_props=None, **kwargs):
    _original_register_page(*args, **kwargs)
    # Resolve page.
    module = kwargs['module'] if 'module' in kwargs else args[0]
    page = dash.page_registry[module]
    # Register callbacks for dynamic props.
    if dynamic_props is not None:
        for component in dynamic_props:
            set_props(component, page['path'], dynamic_props[component])
    # Resolve any dynamic components.
    if dynamic_components is None:
        return
    for component in dynamic_components:
        set_visible(component, page['path'])


dash.register_page = _register_page


# endregion

# region Public interface

def set_default_container(container: Component):
    """
    Per default, dynamic components are rendered into the '_COMPONENT_CONTAINER' declared above.
    Use this function to change the default container.
    :param container: the container into which components will be rendered by default
    :return: None
    """
    _COMPONENT_CONTAINER = container


def assign_container(component: Component, container: Component):
    """
    By default, dynamic components are rendered into the '_COMPONENT_CONTAINER' declared above. Call this function to
    specify that the component should be rendered in a different container.
    :param component: the (dynamic) component in question
    :param container: the container into which the component will be rendered
    :return: None
    """
    if component in _CONTAINER_REGISTRY:
        raise ValueError("You can assign a component to one container.")
    _CONTAINER_REGISTRY[component] = container


def set_visible(component: Component, path: str):
    """
    Register path(s) for which a component should be visible.
    :param component: the (dynamic) component in question
    :param path: the (url) path for which the component should be visible
    :return: None
    """
    _COMPONENT_PATH_REGISTRY.setdefault(component, []).append(path)


def set_props(component: Component, path: str, prop_map: dict[str, Any]):
    """
    Register path(s) for which a particular props should be set.
    :param component: the (dynamic) component in question
    :param path: the (url) path for which the props should be set
    :param prop_map: the props, i.e. (prop name, prop value) pairs
    :return: None
    """
    for prop in prop_map:
        _PROP_PATH_REGISTRY.setdefault(component, OrderedDict()).setdefault(prop, {})[path] = prop_map[prop]


def setup_dynamic_components() -> html.Div:
    """
    Initializes the dynamic components and returns the (default) container into which the components are rendered.
    :return: the default container, into which dynamic components are rendered. Should be included in the layout,
    unless all (dynamic) components are assigned to custom containers (via 'assign_container')
    """
    _setup_callbacks()
    return _COMPONENT_CONTAINER


# endregion

# region Utils

def _prepare_container(container: Optional[Component] = None):
    container = _COMPONENT_CONTAINER if container is None else container
    # Make sure children is a list.
    if container.children is None:
        container.children = []
    if not isinstance(container.children, list):
        container.children = [container.children]
    return container


def _setup_callbacks():
    store = dash.dash._ID_STORE
    location = dash.dash._ID_LOCATION
    # Setup callbacks for dynamic components.
    components = list(_COMPONENT_PATH_REGISTRY.keys())
    for component in components:
        # Wrap in div to ensure 'hidden' prop exists.
        wrapper = html.Div(component, disable_n_clicks=True, hidden=True)
        # Add to container.
        container = _prepare_container(_CONTAINER_REGISTRY.get(component, _COMPONENT_CONTAINER))
        container.children.append(wrapper)
        # Setup callback.
        f = f"""function(y, x){{
            const paths = {_COMPONENT_PATH_REGISTRY[component]}; 
            return !paths.includes(x);
        }}"""
        clientside_callback(f, Output(wrapper, "hidden", allow_duplicate=True),
                            Input(store, "data"),
                            State(location, "pathname"),
                            prevent_initial_call='initial_duplicate')
    # Setup callbacks for dynamic props.
    components = list(_PROP_PATH_REGISTRY.keys())
    for component in components:
        for prop in _PROP_PATH_REGISTRY[component]:
            path_map = _PROP_PATH_REGISTRY[component][prop]
            default = getattr(component, prop, None)
            # Setup callback.
            f = f"""function(y, x){{
                const path_map = JSON.parse(\'{json.dumps(path_map)}\'); 
                console.log(path_map);
                console.log(x);
                if (x in path_map){{
                    console.log("RETURN X");
                    return path_map[x];
                }}
                console.log("RETURN DEFAULT");
                return JSON.parse(\'{json.dumps(default)}\'); 
            }}"""
            clientside_callback(f, Output(component, prop, allow_duplicate=True),
                                Input(store, "data"),
                                State(location, "pathname"),
                                prevent_initial_call='initial_duplicate')

# endregion
