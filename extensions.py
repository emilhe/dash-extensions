import dash
import itertools
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from more_itertools import unique_everseen


class DashCallbackBlueprint:
    def __init__(self, callbacks=None):
        self.callbacks = [] if callbacks is None else callbacks

    def callback(self, outputs, inputs, func, states=None):
        outputs, inputs, states = _as_list(outputs), _as_list(inputs), _as_list(states)
        self.callbacks.append(dict(outputs=outputs, inputs=inputs, func=func, states=states))

    def register(self, dash_app):
        detangled_callbacks = self._untangle_callbacks()
        for callback in detangled_callbacks:
            _register_callback(dash_app, callback)

    def _untangle_callbacks(self):
        # Divide callback into groups based on output overlaps.
        output_key_map = [[".".join(item) for item in callback["outputs"]] for callback in self.callbacks]
        groups = _group_callbacks(output_key_map)
        # Create a single callback for each group.
        untangled_callbacks = []
        for group in groups:
            untangled_callback = _combine_callbacks([self.callbacks[i] for i in group])
            untangled_callbacks.append(untangled_callback)

        return untangled_callbacks


# NOTE: No performance considerations what so ever. Just an initial proof-of-concept implementation.
def _combine_callbacks(callbacks):
    # Setup inputs/outputs/states lists.
    outputs, inputs, states = [], [], None
    for callback in callbacks:
        outputs.extend(callback["outputs"])
        inputs.extend(callback["inputs"])
        if callback["states"] is not None:
            states = [] if states is None else states
            states.extend(callback["states"])
    # Remove duplicates.
    outputs = list(unique_everseen(outputs))
    inputs = list(unique_everseen(inputs))
    states = list(unique_everseen(states))
    # Create input prop mappings.
    input_props = [".".join(item) for item in inputs]
    input_prop_lists = [[".".join(item) for item in callback["inputs"]] for callback in callbacks]
    input_mappings = [[input_props.index(item) for item in l] for l in input_prop_lists]
    # Create state prop mappings.
    state_props = [".".join(item) if item is not None else None for item in states]
    state_prop_lists = [
        [".".join(item) for item in callback["states"]] if callback["states"] is not None else None for callback
        in callbacks]
    state_mappings = [[state_props.index(item) for item in l] if l is not None else None for l in
                      state_prop_lists]
    # Create output prop mappings.
    output_props = [".".join(item) for item in outputs]
    output_prop_lists = [[".".join(item) for item in callback["outputs"]] for callback in callbacks]
    output_mappings = [[output_props.index(item) for item in l] for l in output_prop_lists]

    # TODO: There might be a scope issue here
    def wrapper(*args):
        local_inputs = list(args)[:len(input_prop_lists)]
        local_states = list(args)[len(input_prop_lists):]
        if len(dash.callback_context.triggered) == 0:
            raise PreventUpdate
        prop_id = dash.callback_context.triggered[0]['prop_id']
        output_values = [dash.no_update] * len(outputs)
        for i, entry in enumerate(input_prop_lists):
            # Check if the trigger is an input of the
            if prop_id not in entry:
                continue
            # Trigger the callback function.
            try:
                inputs_i = [local_inputs[j] for j in input_mappings[i]]
                if state_mappings[i] is None:
                    outputs_i = callbacks[i]["func"](*inputs_i)
                else:
                    states_i = [local_states[j] for j in state_mappings[i]]
                    outputs_i = callbacks[i]["func"](*inputs_i, *states_i)
                if len(callbacks[i]["outputs"]) == 1:
                    outputs_i = [outputs_i]
                for j, item in enumerate(outputs_i):
                    output_values[output_mappings[i][j]] = outputs_i[j]
            except PreventUpdate:
                continue
        # Check if an update is needed.
        if all([item == dash.no_update for item in output_values]):
            raise PreventUpdate
        # Return the combined output.
        return output_values if len(output_values) > 1 else output_values[0]

    return {"outputs": outputs, "inputs": inputs, "func": wrapper, "states": states}


# NOTE: No performance considerations what so ever. Just an initial proof-of-concept implementation.
def _group_callbacks(output_ids, groups=None):
    groups = [[i] for i in range(len(output_ids))] if groups is None else groups
    new_groups = []
    accounted_for = []
    done = True
    for i in range(len(groups)):
        if i in accounted_for:
            continue
        group_i = groups[i]
        output_ids_i = set(itertools.chain(*[output_ids[k] for k in group_i]))
        accounted_for.append(i)
        for j in range(i + 1, len(groups)):
            group_j = groups[j]
            output_ids_j = set(itertools.chain(*[output_ids[k] for k in group_j]))
            intersection = output_ids_i.intersection(output_ids_j)
            if len(intersection) > 0:
                group_i.extend(group_j)
                accounted_for.append(j)
                done = False
        new_groups.append(sorted(list(set(group_i))))
    if not done:
        return _group_callbacks(output_ids, new_groups)
    return new_groups


def _register_callback(dash_app, callback):
    # Setup outputs and inputs.
    outputs = Output(*callback["outputs"][0]) if len(callback["outputs"]) == 1 else \
        [Output(*item) for item in callback["outputs"]]
    inputs = [Input(*item) for item in callback["inputs"]]
    # Register callbacks without state.
    if callback["states"] is None:
        dash_app.callback(outputs, inputs)(callback["func"])
        return
    # Register callbacks with state.
    states = [State(*item) for item in callback["states"]]
    dash_app.callback(outputs, inputs, states)(callback["func"])


def _as_list(item):
    if item is None:
        return None
    return item if isinstance(item, list) else [item]
