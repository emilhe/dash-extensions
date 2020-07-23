import functools
import hashlib
import itertools
import json
import operator
import secrets
import dash

from dash.dependencies import Input
from dash.exceptions import PreventUpdate
from flask import session
from flask_caching.backends import FileSystemCache
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
        # Set session secret. Used by some subclasses.
        if not dash_app.server.secret_key:
            dash_app.server.secret_key = secrets.token_urlsafe(16)

    def _resolve_callbacks(self):
        """
         This method resolves the callbacks. While no modifications are performed in the base class, this is the method
         that subclasses should target inject callback modifications.
        """
        return self.callbacks


def _get_session_id(session_key=None):
    session_key = "session_id" if session_key is None else session_key
    # Create unique session id.
    if not session.get(session_key):
        session[session_key] = secrets.token_urlsafe(16)
    return session.get(session_key)


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
    """
     Like an Input, a trigger can trigger a callback, but it's values it not included in the resulting function call.
    """

    def __init__(self, component_id, component_property):
        super().__init__(component_id, component_property)


class CallbackCache(CallbackBlueprint):
    """
    The CallbackCache (CB) class acts as a proxy for the Dash app object in the context of callback registration. It
    exposes a "memoize" decorator, which stores the value returned by the callback in a (key, value) cache and returns
    only the key to the client. For large values, this strategy can drastically reduce network overhead. Furthermore,
    since the values are typically stored as pickles, they do not need to be serialized to/from JSON.

    :param cache: cache backend, see https://flask-caching.readthedocs.io/en/latest/#built-in-cache-backends.
    :param session_check: if True, the values will be stored uniquely per session
    :param instant_refresh: if True, callbacks will be evaluated every time, otherwise only when args change

    """

    def __init__(self, cache=None, session_check=None, instant_refresh=None):
        super().__init__()
        if cache is not None:
            cache.default_timeout = 0  # the default_timeout of the inner cache is ignore
        self.cache = cache if cache is not None else FileSystemCache("cache", default_timeout=0)
        self.cached_callbacks = []
        self.callback_input_fltr = []
        self.callback_instant_refresh = []
        self.session_check = session_check if session_check is not None else True
        self.instant_refresh = instant_refresh if session_check is not None else True

    def cached_callback(self, outputs, inputs, states=None, instant_refresh=None):
        # Save index to keep tract of which callback to cache.
        self.cached_callbacks.append(len(self.callbacks))
        self.callback_input_fltr.append([isinstance(item, Trigger) for item in inputs])
        self.callback_instant_refresh.append(instant_refresh)
        # Save the callback itself.
        return self.callback(outputs, inputs, states)

    def _resolve_callbacks(self):
        # Figure out which IDs are to be cached.
        cached_ids = [[_create_callback_id(i) for i in self.callbacks[j]["outputs"]] for j in self.cached_callbacks]
        cached_ids = functools.reduce(operator.iconcat, cached_ids, [])
        # Modify the callbacks.
        for i, callback in enumerate(self.callbacks):
            # Figure out which args need loading.
            items = callback["inputs"] + callback["states"]
            item_ids = [_create_callback_id(item) for item in items]
            item_is_packed = [item_id in cached_ids for item_id in item_ids]
            # If any arguments are packed, unpack them.
            if any(item_is_packed):
                original_callback = callback["callback"]
                callback["callback"] = self._unpack_outputs(item_is_packed)(original_callback)
            # Check if caching is needed for the current callback.
            caching_needed = i in self.cached_callbacks
            if not caching_needed:
                continue
            # Check inputs to be ignored. TODO: Could be implemented for normal callbacks also?
            args_filter = self.callback_input_fltr[self.cached_callbacks.index(i)]
            if len(callback["states"]) > 0:
                args_filter += [False] * len(callback["states"])
            if any(args_filter):
                original_callback = callback["callback"]
                callback["callback"] = filter_args(args_filter)(original_callback)
            # Do the caching magic.
            original_callback = callback["callback"]
            instant_refresh = self.callback_instant_refresh[self.cached_callbacks.index(i)]
            instant_refresh = instant_refresh if instant_refresh is not None else self.instant_refresh
            callback["callback"] = self._pack_outputs(callback["outputs"], instant_refresh)(original_callback)
        # Return the update callback.
        return self.callbacks

    def _unpack_outputs(self, item_is_packed):
        def unpack(f):
            @functools.wraps(f)
            def decorated_function(*args):
                if not any(item_is_packed):
                    return f(*args)
                args = list(args)
                for i, packed in enumerate(item_is_packed):
                    # Just skip elements that are not cached.
                    if not packed:
                        continue
                    # Replace content of cached element(s).
                    args[i] = self.cache.get(args[i])
                return f(*args)

            return decorated_function

        return unpack

    def _pack_outputs(self, outputs, instant_refresh):
        def packed_callback(f):
            @functools.wraps(f)
            def decorated_function(*args):
                # Check if the data is there.
                multi_output = len(outputs) > 1
                unique_ids = [_get_cache_id(f, output, list(args), self.session_check) for output in outputs]
                update_needed = [not self.cache.has(uid) for uid in unique_ids]
                # If it's not, calculate it.
                if any(update_needed) or instant_refresh:
                    data = f(*args)
                    data = data if multi_output else [data]
                    for i, uid in enumerate(unique_ids):
                        self.cache.set(uid, data[i])
                # Return the id(s).
                return unique_ids if multi_output else unique_ids[0]

            return decorated_function

        return packed_callback


def filter_args(args_filter):
    def filter_args(f):
        @functools.wraps(f)
        def decorated_function(*args):
            filtered_args = [arg for j, arg in enumerate(args) if not args_filter[j]]
            return f(*filtered_args)

        return decorated_function

    return filter_args


def _get_cache_id(func, output, args, session_check=None):
    all_args = [func.__name__, _create_callback_id(output)] + list(args)
    if session_check:
        all_args += [_get_session_id()]
    return hashlib.md5(json.dumps(all_args).encode()).hexdigest()


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
