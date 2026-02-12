import importlib

# region Random component id generation

_components_with_random_ids = []
_set_random_id = None

try:
    _component_class = importlib.import_module("dash.development.base_component").Component
    _set_random_id = _component_class._set_random_id
except Exception:
    _component_class = None


def _collect_components_with_random_ids(self):
    if getattr(self, "id", None) is None:
        _components_with_random_ids.append(self)
    if _set_random_id is None:
        return getattr(self, "id", None)
    return _set_random_id(self)


if _component_class is not None:
    _component_class._set_random_id = _collect_components_with_random_ids


def assert_no_random_ids():
    """
    When a component is referenced in a callback, a random id is assigned automatically, if an id is not already set.
    This operation makes the application _stateful_, which is *not* recommended. This function raises an assertion
    error if any components have been assigned random ids, thereby forcing the developer to set ids for all components.
    """
    if not _components_with_random_ids:
        return
    raise AssertionError(
        f"The following components have random ids: {', '.join([str(c) for c in _components_with_random_ids])}"
    )


# endregion
