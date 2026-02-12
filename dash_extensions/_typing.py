from typing import Any, Protocol, TypeAlias


class ComponentProtocol(Protocol):
    id: Any
    children: Any


try:
    from dash.development.base_component import Component as _DashComponent
except (ImportError, AttributeError):
    Component: TypeAlias = ComponentProtocol
else:
    Component: TypeAlias = _DashComponent | ComponentProtocol

try:
    from dash.dependencies import Wildcard as _DashWildcard
except (ImportError, AttributeError):
    Wildcard: TypeAlias = object
else:
    Wildcard: TypeAlias = _DashWildcard


# Compat shims for Dash internals that may move across major versions.

try:
    from dash._callback_context import context_value
except (ImportError, AttributeError):
    context_value = None

try:
    from dash._callback_context import _get_context_value
except (ImportError, AttributeError):
    _get_context_value = None

try:
    from dash._utils import stringify_id
except (ImportError, AttributeError):
    stringify_id = None
