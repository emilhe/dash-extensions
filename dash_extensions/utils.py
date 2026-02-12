from typing import TypeVar

from dash_extensions._typing import Component
ComponentIdentifier = str | dict | Component
DashNode = Component | list[Component] | str | list[str]

T = TypeVar("T")


def get_id(component: ComponentIdentifier) -> str | dict:
    if hasattr(component, "_set_random_id"):
        return component._set_random_id()  # type: ignore[union-attr]
    return component


def as_list(item: T | list[T] | None) -> list[T]:
    if item is None:
        return []
    if isinstance(item, tuple):
        return list(item)
    if isinstance(item, list):
        return item
    return [item]
