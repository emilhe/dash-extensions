from typing import Any, Protocol, TypeAlias

from dash import ALL, ALLSMALLER, MATCH


class ComponentProtocol(Protocol):
    id: Any
    children: Any


try:
    from dash.development.base_component import Component as _DashComponent
except Exception:
    Component: TypeAlias = ComponentProtocol
else:
    Component: TypeAlias = _DashComponent | ComponentProtocol

try:
    from dash.dependencies import Wildcard as _DashWildcard
except Exception:
    Wildcard: TypeAlias = object
else:
    Wildcard: TypeAlias = _DashWildcard


def is_wildcard(value: object) -> bool:
    return value in (ALL, MATCH, ALLSMALLER)


# Compat shims for Dash internals that may move across major versions.

try:
    from dash._callback_context import context_value
except Exception:
    context_value = None

try:
    from dash._callback_context import _get_context_value
except Exception:
    _get_context_value = None

try:
    from dash._utils import stringify_id
except Exception:
    stringify_id = None
