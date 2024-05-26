import dash.dependencies

# region Random component id generation

_set_random_id = dash.development.base_component.Component._set_random_id
_components_with_random_ids = []


def _collect_components_with_random_ids(self):
    if not hasattr(self, "id"):
        _components_with_random_ids.append(self)
    return _set_random_id(self)


dash.development.base_component.Component._set_random_id = (
    _collect_components_with_random_ids
)


def assert_no_random_ids():
    """
    When a component is referenced in a callback, a random id is assigned automatically, if an id is not already set.
    This operation makes the application _stateful_, which is *not* recommended. This function raises an assertion
    error if any components have been assigned random ids, thereby forcing the developer to set ids for all components.
    """
    if _components_with_random_ids:
        return
    raise AssertionError(
        f"The following components have random ids: {', '.join([str(c) for c in _components_with_random_ids])}"
    )


# endregion
