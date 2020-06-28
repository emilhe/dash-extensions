import hashlib
import os
import json
import pickle
import datetime

import dash
import itertools

from dash.exceptions import PreventUpdate
from more_itertools import unique_everseen


# region Callback decorator

class CallbackDecorator:
    def __init__(self):
        self.callbacks = []

    def callback(self, outputs, inputs, states=None):
        outputs, inputs, states = _as_list(outputs), _as_list(inputs), _as_list(states)
        self.callbacks.append(dict(outputs=outputs, inputs=inputs, states=states))

        def cache_func(func):
            self.callbacks[-1]["callback"] = func

        return cache_func

    def register(self, dash_app):
        callbacks = self._resolve_callbacks()
        for callback in callbacks:
            _register_callback(dash_app, callback)

    def _resolve_callbacks(self):
        pass


def _register_callback(dash_app, callback):
    outputs = callback["outputs"][0] if len(callback["outputs"]) == 1 else callback["outputs"]
    dash_app.callback(outputs, callback["inputs"], callback["states"])(callback["callback"])


def _as_list(item):
    if item is None:
        return []
    return item if isinstance(item, list) else [item]


# endregion

# region Disk cache

class DashDiskCache(CallbackDecorator):

    def __init__(self, cache_dir, expire_after=None, makedirs=None):
        super().__init__()
        self.cache_dir = cache_dir
        self.expire_after = expire_after if expire_after is not None else -1
        self.cached_callbacks = []
        if makedirs or makedirs is None:
            os.makedirs(self.cache_dir, exist_ok=True)

    def cached_callback(self, outputs, inputs, states=None):
        # Save index to keep tract of which callback to cache.
        self.cached_callbacks.append(len(self.callbacks))
        # Save the callback itself.
        return self.callback(outputs, inputs, states)

    def _resolve_callbacks(self):
        cached_ids = []
        # Step one, wrap the cached_callbacks.
        for idx in self.cached_callbacks:
            callback = self.callbacks[idx]
            # Collect the ids of components, which are cached server side.
            cached_ids.extend([_create_callback_id(item) for item in callback["outputs"]])
            # Modify the callback to return md5 hash.
            original_callback = callback["callback"]
            callback["callback"] = lambda *args, x=original_callback, y=callback["outputs"]: \
                self._dump_callback(x, y, *args)
        # Step two, wrap all of the other callbacks.
        for i, callback in enumerate(self.callbacks):
            # Figure out which args need loading.
            items = callback["inputs"] + callback["states"]
            item_ids = [_create_callback_id(item) for item in items]
            item_is_cached = [item_id in cached_ids for item_id in item_ids]
            # Nothing to load, just proceed.
            if not any(item_is_cached):
                continue
            # Do magic.
            original_callback = callback["callback"]
            callback["callback"] = lambda *args, x=original_callback, y=item_is_cached: \
                self._load_callback(x, y, *args)
        # Return the update callback.
        return self.callbacks

    def _get_path(self, unique_id):
        return os.path.join(self.cache_dir, unique_id)

    def _dump_callback(self, func, outputs, *args):
        data = None
        multi_output = len(outputs) > 1
        unique_ids = []
        for i, output in enumerate(outputs):
            # Get file cache path.
            unique_id = _get_id(func, output, args)
            target = self._get_path(unique_id)
            # Check if cache refresh is needed.
            refresh_needed = True
            if self.expire_after != 0:  # zero means ALWAYS refresh
                if os.path.isfile(target):
                    refresh_needed = self.expire_after > 0  # minus means NEVER expire
                    if refresh_needed:
                        age = (datetime.datetime.now() -
                               datetime.datetime.fromtimestamp(os.path.getmtime(target))).total_seconds()
                        refresh_needed = age > self.expire_after
            # Refresh the data.
            if refresh_needed:
                data = func(*args) if data is None else data  # load data only once
                with open(target, 'wb') as f:
                    pickle.dump(data[i] if multi_output else data, f)
            # Collect output id(s).
            unique_ids.append(unique_id)
        # Return the id rather than the function data.
        return unique_ids if multi_output else unique_ids[0]

    def _load_callback(self, func, item_is_cached, *args):
        args = list(args)
        for i, is_cached in enumerate(item_is_cached):
            # Just skip elements that are not cached.
            if not is_cached:
                continue
            # Replace content of cached element(s).
            target = self._get_path(args[i])
            with open(target, 'rb') as f:
                args[i] = pickle.load(f)
        return func(*args)


def _get_id(func, output, args):
    return hashlib.md5(json.dumps([func.__name__, _create_callback_id(output)] + list(args)).encode()).hexdigest()


# endregion

# region Callback blueprint

class DashCallbackBlueprint(CallbackDecorator):
    def __init__(self):
        super().__init__()

    def _resolve_callbacks(self):
        # Divide callback into groups based on output overlaps.
        output_key_map = [[_create_callback_id(item) for item in callback["outputs"]] for callback in self.callbacks]
        groups = _group_callbacks(output_key_map)
        # Create a single callback for each group.
        untangled_callbacks = []
        for group in groups:
            untangled_callback = _combine_callbacks([self.callbacks[i] for i in group])
            untangled_callbacks.append(untangled_callback)

        return untangled_callbacks


# NOTE: No performance considerations what so ever. Just an initial proof-of-concept implementation.
def _combine_callbacks(callbacks):
    inputs, input_props, input_prop_lists, input_mappings = _prep_props(callbacks, "inputs")
    states, state_props, state_prop_lists, state_mappings = _prep_props(callbacks, "states")
    outputs, output_props, output_prop_lists, output_mappings = _prep_props(callbacks, "outputs")

    # TODO: There might be a scope issue here
    def wrapper(*args):
        local_inputs = list(args)[:len(inputs)]
        local_states = list(args)[len(inputs):]
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
                states_i = [local_states[j] for j in state_mappings[i]]
                outputs_i = callbacks[i]["callback"](*inputs_i, *states_i)
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

    return {"outputs": outputs, "inputs": inputs, "callback": wrapper, "states": states}


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


def _prep_props(callbacks, key):
    all = []
    for callback in callbacks:
        all.extend(callback[key])
    all = list(unique_everseen(all))
    props = [_create_callback_id(item) for item in all]
    prop_lists = [[_create_callback_id(item) for item in callback[key]] for callback in callbacks]
    mappings = [[props.index(item) for item in l] for l in prop_lists]
    return all, props, prop_lists, mappings


def _create_callback_id(item):
    return "{}.{}".format(item.component_id, item.component_property)


# endregion

# region Get trigger


class Trigger(object):
    def __init__(self, id, **kwargs):
        self.id = id
        for key in kwargs:
            setattr(self, key, kwargs[key])


def get_trigger():
    triggered = dash.callback_context.triggered
    if not triggered:
        return Trigger(None)
    # Collect trigger ids and values.
    trigger_id = None
    trigger_values = {}
    for entry in triggered:
        tmp = entry['prop_id'].split(".")
        # Determine the trigger object.
        if trigger_id is None:
            trigger_id = tmp[0]
        # TODO: Should all properties of the trigger be registered, or only one?
        if trigger_id != tmp[0]:
            continue
        trigger_values[tmp[1]] = entry['value']
    # Now, create an object.
    try:
        trigger_id = json.loads(trigger_id)
    except ValueError:
        pass
    return Trigger(trigger_id, **trigger_values)

# endregion
