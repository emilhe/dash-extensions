import dash
from collections import OrderedDict
from typing import Optional
from dash import html, Input, Output, clientside_callback
from dash.development.base_component import Component

"""
This module holds utilities related to the [Dash pages](https://dash.plotly.com/urls).
"""

_ID_CONTENT = "_component_content"
_PATH_REGISTRY = OrderedDict()
_CONTAINER_REGISTRY = {}
_COMPONENT_CONTAINER = html.Div(id=_ID_CONTENT, disable_n_clicks=True)

# region Monkey patch page registration function

_original_register_page = dash.register_page


def _register_page(*args, components=None, **kwargs):
    _original_register_page(*args, **kwargs)
    if components is None:
        return
    module = kwargs['module'] if 'module' in kwargs else args[0]
    page = dash.page_registry[module]
    for component in components:
        set_visible(component, page['path'])


dash.register_page = _register_page


# endregion

# region Public interface

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
    _PATH_REGISTRY.setdefault(component, []).append(path)


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
    location = dash.dash._ID_LOCATION
    components = list(_PATH_REGISTRY.keys())
    for component in components:
        # Wrap in div to ensure 'hidden' prop exists.
        wrapper = html.Div(component, disable_n_clicks=True, hidden=True)
        # Add to container.
        container = _prepare_container(_CONTAINER_REGISTRY.get(component, _COMPONENT_CONTAINER))
        container.children.append(wrapper)
        # Setup callback.
        f = f"function(x){{const paths = {_PATH_REGISTRY[component]}; return !paths.includes(x);}}"
        clientside_callback(f, Output(wrapper, "hidden"), Input(location, "pathname"))

# endregion
