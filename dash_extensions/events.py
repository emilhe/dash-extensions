import datetime
import re
from enum import Enum
from logging import getLogger
from typing import Optional, Type, TypeVar

from dash import ctx, set_props
from dash.dependencies import DashDependency
from pydantic import BaseModel, Field

from dash_extensions.enrich import Input, dcc

logger = getLogger(__name__)


T = TypeVar("T", bound=DashDependency)


class EventModel(BaseModel):
    """
    The EventModel class provides the main interface for creating and dispatching events.
    """

    timestamp: float = Field(default_factory=lambda: datetime.datetime.now().timestamp())

    def add_listener(self) -> Input:
        """
        Listen for event.
        """
        return self.get_dependency(Input)

    def dispatch(self):
        """
        Dispatch event.
        """
        if self._component_id not in _event_registry:
            logger.warning(f"No listener registered for {self._uid}. Event dispatch suppressed.")
            return
        set_props(self._component_id, {"data": self.model_dump()})

    def get_dependency(self, dependency_type: Type[T]) -> T:
        """
        Get DashDependency (Input, Output, State) for event.
        """
        _register_event(self)  # TODO: Could also be on init?
        return dependency_type(self._component_id, "data")

    def is_trigger(self) -> bool:
        return self._component_id in ctx.triggered_prop_ids.values()

    @property
    def _uid(self) -> str:
        raise NotImplementedError

    @property
    def _component_id(self) -> str:
        return f"event_store_{self._uid}"


# region Simple interface (str, Enum; without payload)


class SimpleEvent(EventModel):
    """
    Wrapper class for simple events.
    """

    type: str | Enum | None = None

    def __init__(self, **data):
        if "type" not in data:
            data["type"] = self.__class__.__name__
        super().__init__(**data)

    @classmethod
    def add_listener(cls) -> Input:
        return add_event_listener(cls.__name__)

    @property
    def _uid(self) -> str:
        return _get_event_id(self.type)


def _get_event_id(event: str | Enum) -> str:
    if isinstance(event, Enum):
        event_tag = event.name.lower()
        event_type = _to_snake(event.__class__.__name__)
        return f"{event_type}_{event_tag}"
    return event


def _to_snake(camel: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()


def _base_event(event: str | Enum) -> SimpleEvent:
    return SimpleEvent(type=event)


def dispatch_event(event: str | Enum):
    """
    Dispatch an event.
    """
    return _base_event(event).dispatch()


def get_event_dependency(event: str | Enum, dependency_type: Type[T]) -> T:
    """
    Get DashDependency (Input, Output, State) for a particular event type.
    """
    return _base_event(event).get_dependency(dependency_type)


def add_event_listener(event: str | Enum) -> Input:
    """
    Listen for a particular event type.
    """
    return _base_event(event).get_dependency(Input)


def register_event(event: str | Enum):
    """
    Register an event.
    """
    _register_event(_base_event(event))


def is_event_trigger(event: str | Enum | list[str | Enum]) -> bool:
    """
    Check if an event is a trigger of the callback.
    """
    events = [event] if not isinstance(event, list) else event
    return get_event_trigger(events) is not None


def get_event_trigger(events: list[str | Enum]) -> Optional[str | Enum]:
    """
    Get the event that triggered the callback.
    """
    for event in events:
        if _base_event(event).is_trigger():
            return event
    return None


# endregion

# region Event registry


def resolve_event_components() -> list[dcc.Store]:
    """
    Returns the components that must be included in the layout.
    """
    return [dcc.Store(id=component_id, storage_type="memory") for component_id in list(_event_registry)]


def _register_event(event: EventModel):
    _event_registry.add(event._component_id)


"""
Registry over all events that have dependencies.
"""
_event_registry: set[str] = set()

# endregion
