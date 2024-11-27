from datetime import datetime
from typing import Optional

from dash import Input, dcc, set_props


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


def add_event_listener(event: str) -> Input:
    """
    Listen for a particular event type.
    """
    _event_registry.add(event)
    return Input(_get_event_id(event), "data")


def resolve_event_components() -> list[dcc.Store]:
    """
    Returns the components that must be included in the layout.
    """
    return [dcc.Store(id=_get_event_id(event), storage_type="memory") for event in list(_event_registry)]


def _get_event_id(event: str) -> str:
    return f"event_store_{event}"


"""
Registry over all event that have listeners.
"""
_event_registry = set()
