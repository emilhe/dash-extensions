from datetime import datetime
from enum import Enum
import re
from typing import Optional, Type, TypeVar

from dash import set_props, ctx
from dash_extensions.enrich import Input, dcc
from dash.dependencies import DashDependency

T = TypeVar("T", bound=DashDependency)

Event = str | Enum


def build_event(event: Event, payload: Optional[dict] = None) -> dict:
    """
    Build an event object structure.
    """
    return {
        "data": {
            "type": event,
            "timestamp": datetime.now().timestamp(),
            **({"payload": payload} or {}),
        }
    }


def dispatch_event(event: Event, payload: Optional[dict] = None):
    """
    Dispatch an event.
    """
    set_props(
        _get_event_id(event),
        build_event(event, payload),
    )


def get_event_dependency(event: Event, dependency_type: Type[T]) -> T:
    """
    Get DashDependency (Input, Output, State) for a particular event type.
    """
    _event_registry.add(event)
    return dependency_type(_get_event_id(event), "data")


def add_event_listener(event: Event) -> Input:
    """
    Listen for a particular event type.
    """
    return get_event_dependency(event, Input)


def resolve_event_components() -> list[dcc.Store]:
    """
    Returns the components that must be included in the layout.
    """
    return [dcc.Store(id=_get_event_id(event), storage_type="memory") for event in list(_event_registry)]


def is_event_trigger(event: Event | list[Event]) -> bool:
    """
    Check if an event is a trigger of the callback.
    """
    events = [event] if not isinstance(event, list) else event
    return get_event_trigger(events) is not None


def get_event_trigger(events: list[Event]) -> Optional[Event]:
    """
    Get the event that triggered the callback.
    """
    matches = [event for event in events if _get_event_id(event) in ctx.triggered_prop_ids.values()]
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(f"Multiple events {matches} triggered the callback.")
    return matches[0]


def _to_snake(camel: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()


def _get_event_id(event: Event) -> str:
    event_tag = event.name.lower() if isinstance(event, Enum) else event
    event_type = _to_snake(event.__class__.__name__) if isinstance(event, Enum) else "event"
    return f"{event_type}_{event_tag}_store"


"""
Registry over all events that have dependencies.
"""
_event_registry = set()
