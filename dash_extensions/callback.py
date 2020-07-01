import functools
import hashlib
import operator
import os
import json
import pickle
import datetime

import dash
import itertools

from dash.dependencies import Input
from dash.exceptions import PreventUpdate
from more_itertools import unique_everseen


# region Callback blueprint

class CallbackBlueprint:
    """
    The CallbackBlueprint (CB) class acts as a proxy for the Dash app object in the context of callback registration.
    To bind the callbacks registered on a CB to a Dash app, the "register" function must be called.
    """

    def __init__(self):
        self.callbacks = []

    def callback(self, outputs, inputs, states=None):
        """
        This method mirrors the callback decorator of the Dash app object, but simply caches the inputs.
        """
        outputs, inputs, states = _as_list(outputs), _as_list(inputs), _as_list(states)
        self.callbacks.append(dict(outputs=outputs, inputs=inputs, states=states))

        def cache_func(func):
            self.callbacks[-1]["callback"] = func

        return cache_func

    def register(self, dash_app):
        """
        This method registers the cached callbacks on the Dash app object.
        """
        callbacks = self._resolve_callbacks()
        for callback in callbacks:
            _register_callback(dash_app, callback)

    def _resolve_callbacks(self):
        """
         This method resolves the callbacks. While no modifications are performed in the base class, this is the method
         that subclasses should target inject callback modifications.
        """
        return self.callbacks


def _register_callback(dash_app, callback):
    outputs = callback["outputs"][0] if len(callback["outputs"]) == 1 else callback["outputs"]
    dash_app.callback(outputs, callback["inputs"], callback["states"])(callback["callback"])


def _as_list(item):
    if item is None:
        return []
    return item if isinstance(item, list) else [item]


def _create_callback_id(item):
    return "{}.{}".format(item.component_id, item.component_property)


# endregion

# region Callback cache

class Trigger(Input):
    def __init__(self, component_id, component_property):
        super().__init__(component_id, component_property)


class DiskCache:
    def __init__(self, cache_dir, makedirs=None):
        self.cache_dir = cache_dir
        if makedirs or makedirs is None:
            os.makedirs(self.cache_dir, exist_ok=True)

    def load(self, unique_id):
        with open(self._get_path(unique_id), 'rb') as f:
            data = pickle.load(f)
        return data

    def dump(self, data, unique_id):
        with open(self._get_path(unique_id), 'wb') as f:
            pickle.dump(data, f)

    def contains(self, unique_id):
        return os.path.isfile(self._get_path(unique_id))

    def modified(self, unique_id):
        return datetime.datetime.fromtimestamp(os.path.getmtime(self._get_path(unique_id)))

    def _get_path(self, unique_id):
        return os.path.join(self.cache_dir, unique_id)


class CallbackCache(CallbackBlueprint):

    def __init__(self, cache, expire_after=None):
        super().__init__()
        self.cache = cache
        self.expire_after = expire_after if expire_after is not None else 0
        self.cached_callbacks = []
        self.cached_callbacks_input_fltr = []

    def cached_callback(self, outputs, inputs, states=None):
        # Save index to keep tract of which callback to cache.
        self.cached_callbacks.append(len(self.callbacks))
        self.cached_callbacks_input_fltr.append([isinstance(item, Trigger) for item in inputs])
        # Save the callback itself.
        return self.callback(outputs, inputs, states)

    def _resolve_callbacks(self):
        # Figure out which IDs are cached.
        cached_ids = [[_create_callback_id(i) for i in self.callbacks[j]["outputs"]] for j in self.cached_callbacks]
        cached_ids = functools.reduce(operator.iconcat, cached_ids, [])
        # Modify the callbacks.
        for i, callback in enumerate(self.callbacks):
            # Check if caching is needed.
            caching_needed = i in self.cached_callbacks
            # Figure out which args need loading.
            items = callback["inputs"] + callback["states"]
            item_ids = [_create_callback_id(item) for item in items]
            item_is_cached = [item_id in cached_ids for item_id in item_ids]
            # Nothing modifications needed, just proceed.
            if not caching_needed and not any(item_is_cached):
                continue
            # Create reference to original callback.
            original_callback = callback["callback"]
            # If caching of outputs is not needed, just load the args.
            if not caching_needed:
                callback["callback"] = lambda *args, x=original_callback, y=item_is_cached: \
                    x(*self._load_args(y, *args))
                continue
            # Check inputs to be ignored. TODO: Could be implemented for normal callbacks also?
            arg_fltr = self.cached_callbacks_input_fltr[self.cached_callbacks.index(i)]
            if len(callback["states"]) > 0:
                arg_fltr += [False] * len(callback["states"])
            # If caching is needed, do it.
            callback["callback"] = lambda *args, x=original_callback, y=callback["outputs"], z=item_is_cached, t=arg_fltr: \
                self._dump_callback(x, y, z, *[arg for j, arg in enumerate(args) if not t[j]])
        # Return the update callback.
        return self.callbacks

    def _dump_callback(self, func, outputs, item_is_cached, *args):
        data = None
        multi_output = len(outputs) > 1
        unique_ids = []
        for i, output in enumerate(outputs):
            unique_id = _get_id(func, output, args)
            # Check if cache refresh is needed.
            refresh_needed = True
            if self.expire_after != 0:  # zero means ALWAYS refresh
                if self.cache.contains(unique_id):
                    refresh_needed = self.expire_after > 0  # minus means NEVER expire
                    if refresh_needed:
                        age = (datetime.datetime.now() - self.cache.modified(unique_id)).total_seconds()
                        refresh_needed = age > self.expire_after
            # Refresh the data.
            if refresh_needed:
                # Modify the inputs.
                args = self._load_args(item_is_cached, *args)
                data = func(*args) if data is None else data  # load data only once
                self.cache.dump(data[i] if multi_output else data, unique_id)
            # Collect output id(s).
            unique_ids.append(unique_id)
        # Return the id rather than the function data.
        return unique_ids if multi_output else unique_ids[0]

    def _load_args(self, item_is_cached, *args):
        if not any(item_is_cached):
            return args
        args = list(args)
        for i, is_cached in enumerate(item_is_cached):
            # Just skip elements that are not cached.
            if not is_cached:
                continue
            # Replace content of cached element(s).
            args[i] = self.cache.load(args[i])
        return args


def _get_id(func, output, args):
    return hashlib.md5(json.dumps([func.__name__, _create_callback_id(output)] + list(args)).encode()).hexdigest()


# endregion

# region Callback grouper

class CallbackGrouper(CallbackBlueprint):
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


# endregion

# region Get triggered


class Triggered(object):
    def __init__(self, id, **kwargs):
        self.id = id
        for key in kwargs:
            setattr(self, key, kwargs[key])


def get_triggered():
    triggered = dash.callback_context.triggered
    if not triggered:
        return Triggered(None)
    # Collect trigger ids and values.
    triggered_id = None
    triggered_values = {}
    for entry in triggered:
        # TODO: Test this part.
        elements = entry['prop_id'].split(".")
        current_id = ".".join(elements[:-1])
        current_prop = elements[-1]
        # Determine the trigger object.
        if triggered_id is None:
            triggered_id = current_id
        # TODO: Should all properties of the trigger be registered, or only one?
        if triggered_id != current_id:
            continue
        triggered_values[current_prop] = entry['value']
    # Now, create an object.
    try:
        triggered_id = json.loads(triggered_id)
    except ValueError:
        pass
    return Triggered(triggered_id, **triggered_values)

# endregion
