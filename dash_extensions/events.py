from datetime import datetime
from typing import Optional, Type, TypeVar

from dash import set_props
from dash_extensions.enrich import Input, dcc
from dash.dependencies import DashDependency

T = TypeVar("T", bound=DashDependency)


def dispatch_event(event: str, payload: Optional[dict] = None):
    """
    Dispatch an event.
    """
    set_props(
        _get_event_id(event),
        {
            "data": {
                "type": event,
                "timestamp": datetime.now().timestamp(),
                **(payload or {}),
            }
        },
    )


def get_event_dependency(event: str, dependency_type: Type[T]) -> T:
    """
    Get DashDependency (Input, Output, State) for a particular event type.
    """
    _event_registry.add(event)
    return dependency_type(_get_event_id(event), "data")


def add_event_listener(event: str) -> Input:
    """
    Listen for a particular event type.
    """
    return get_event_dependency(event, Input)


def resolve_event_components() -> list[dcc.Store]:
    """
    Returns the components that must be included in the layout.
    """
    return [dcc.Store(id=_get_event_id(event), storage_type="memory") for event in list(_event_registry)]


def _get_event_id(event: str) -> str:
    return f"event_store_{event}"


"""
Registry over all events that have dependencies.
"""
_event_registry = set()
