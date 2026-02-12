from typing import Any, Protocol, TypeAlias


class ComponentProtocol(Protocol):
    id: Any
    children: Any


try:
    from dash.development.base_component import Component as _DashComponent
except Exception:
    Component: TypeAlias = ComponentProtocol
else:
    Component: TypeAlias = _DashComponent | ComponentProtocol
