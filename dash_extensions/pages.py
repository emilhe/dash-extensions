import json
import uuid
from collections import OrderedDict
from typing import Any, Optional

import dash
from dash import Input, Output, State, clientside_callback, html, page_container

from dash_extensions._typing import Component


"""
This module holds utilities related to the [Dash pages](https://dash.plotly.com/urls).
"""

_ID_CONTENT = "_component_content"
_COMPONENT_PATH_REGISTRY: dict[Component, list[str]] = OrderedDict()
_PROP_PATH_REGISTRY: dict[Component, dict[str, list[str]]] = OrderedDict()
_CONTAINER_REGISTRY: dict[Component, Component] = {}
_COMPONENT_CONTAINER = html.Div(id=_ID_CONTENT, disable_n_clicks=True, style=dict(display="contents"))

# region Monkey patch page registration function

_original_register_page = dash.register_page


def _register_page(*args, page_components=None, page_properties=None, **kwargs):
    _original_register_page(*args, **kwargs)
    # Resolve page.
    module = kwargs["module"] if "module" in kwargs else args[0]
    page = dash.page_registry[module]
    # Register callbacks for page props.
    if page_properties is not None:
        for component in page_properties:
            _set_props(component, page["path"], page_properties[component])
    # Resolve any page components.
    if page_components is None:
        return
    for component in page_components:
        _set_visible(component, page["path"])


dash.register_page = _register_page


# endregion

# region Public interface


def set_page_container_style_display_contents():
    """
    Changes the style of the page container (and the page content container) so that their children are rendered
    as if they were children of the page container's parent (see https://caniuse.com/css-display-contents). This is
    an advantage if you are using css grid, as it makes it possible to mix the page components with other components.
    """
    page_container.style = dict(display="contents")
    for child in page_container.children:
        if child.id == "_pages_content":
            child.style = dict(display="contents")


def set_default_container(container: Component):
    """
    Per default, page components are rendered into the '_COMPONENT_CONTAINER' declared above.
    Use this function to change the default container.
    :param container: the container into which page components will be rendered by default
    :return: None
    """
    global _COMPONENT_CONTAINER
    _COMPONENT_CONTAINER = container


def assign_container(component: Component, container: Component):
    """
    By default, page components are rendered into the '_COMPONENT_CONTAINER' declared above. Call this function to
    specify that the component should be rendered in a different container.
    :param component: the (page) component in question
    :param container: the container into which the component will be rendered
    :return: None
    """
    if component in _CONTAINER_REGISTRY:
        raise ValueError("You can assign a component to one container.")
    _CONTAINER_REGISTRY[component] = container


def _set_visible(component: Component, path: str):
    """
    Register path(s) for which a component should be visible.
    :param component: the (page) component in question
    :param path: the (url) path for which the component should be visible
    :return: None
    """
    _COMPONENT_PATH_REGISTRY.setdefault(component, []).append(path)


def _set_props(component: Component, path: str, prop_map: dict[str, Any]):
    """
    Register path(s) for which a particular props should be set.
    :param component: the (page) component in question
    :param path: the (url) path for which the props should be set
    :param prop_map: the props, i.e. (prop name, prop value) pairs
    :return: None
    """
    for prop in prop_map:
        _PROP_PATH_REGISTRY.setdefault(component, OrderedDict()).setdefault(prop, {})[path] = prop_map[prop]


def setup_page_components() -> html.Div:
    """
    Initializes the page components and returns the (default) container into which the components are rendered.
    :return: the default container, into which page components are rendered. Must be included in the layout,
    unless all (page) components are assigned to custom containers (via 'assign_container')
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
    store, location = "_pages_store", "_pages_location"
    # Setup callbacks for page components.
    components = list(_COMPONENT_PATH_REGISTRY.keys())
    for component in components:
        # Wrap in div container, so we can hide it.
        component_id = getattr(component, "id", None)
        # TODO: UUID fallback is non-deterministic across restarts; fine since the original _set_random_id was too.
        wrapper_id = f"{component_id}_wrapper" if component_id is not None else f"{uuid.uuid4().hex}_wrapper"
        wrapper = html.Div(
            component,
            disable_n_clicks=True,
            style=dict(display="none"),
            id=wrapper_id,
        )
        # Add to container.
        container = _prepare_container(_CONTAINER_REGISTRY.get(component, _COMPONENT_CONTAINER))
        container.children.append(wrapper)
        # Setup callback.
        f = f"""function(y, x){{
            const paths = {_COMPONENT_PATH_REGISTRY[component]};
            if(paths.includes(x)){{
                return {{display: "contents"}};
            }}
            return {{display: "none"}};
        }}"""
        clientside_callback(
            f,
            Output(wrapper, "style", allow_duplicate=True),
            Input(store, "data"),
            State(location, "pathname"),
            prevent_initial_call="initial_duplicate",
        )
    # Setup callbacks for page props.
    components = list(_PROP_PATH_REGISTRY.keys())
    for component in components:
        for prop in _PROP_PATH_REGISTRY[component]:
            path_map = _PROP_PATH_REGISTRY[component][prop]
            default = getattr(component, prop, None)
            # Setup callback.
            f = f"""function(y, x){{
                const path_map = JSON.parse(\'{json.dumps(path_map)}\');
                if (x in path_map){{
                    return path_map[x];
                }}
                return JSON.parse(\'{json.dumps(default)}\');
            }}"""
            clientside_callback(
                f,
                Output(component, prop, allow_duplicate=True),
                Input(store, "data"),
                State(location, "pathname"),
                prevent_initial_call="initial_duplicate",
            )


# endregion
