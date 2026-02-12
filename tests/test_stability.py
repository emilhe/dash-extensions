import pytest

import dash_extensions.enrich
from dash_extensions.enrich import CallbackBlueprint, DashBlueprint, Input, Output
from dash_extensions import validate


def test_resolve_callbacks_does_not_mutate_blueprint_state():
    local_blueprint = DashBlueprint(include_global_callbacks=True)
    local_cb = CallbackBlueprint(Output("local-out", "children"), Input("local-in", "value"))
    local_cb.f = lambda value: value
    local_blueprint.callbacks.append(local_cb)

    global_blueprint = DashBlueprint()
    global_cb = CallbackBlueprint(Output("global-out", "children"), Input("global-in", "value"))
    global_cb.f = lambda value: value
    global_blueprint.callbacks.append(global_cb)

    original_global_blueprint = dash_extensions.enrich.GLOBAL_BLUEPRINT
    try:
        dash_extensions.enrich.GLOBAL_BLUEPRINT = global_blueprint

        callbacks_1, _ = local_blueprint._resolve_callbacks()
        callbacks_2, _ = local_blueprint._resolve_callbacks()

        assert len(callbacks_1) == 2
        assert len(callbacks_2) == 2
        assert len(local_blueprint.callbacks) == 1
    finally:
        dash_extensions.enrich.GLOBAL_BLUEPRINT = original_global_blueprint


def test_assert_no_random_ids_passes_when_no_random_ids():
    validate._components_with_random_ids.clear()
    validate.assert_no_random_ids()


def test_assert_no_random_ids_raises_when_random_ids_exist():
    validate._components_with_random_ids.clear()
    validate._components_with_random_ids.append("dummy")
    with pytest.raises(AssertionError):
        validate.assert_no_random_ids()
    validate._components_with_random_ids.clear()
