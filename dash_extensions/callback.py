import functools
import hashlib
import json
import pickle
import secrets
import uuid
import dash
import dash_html_components as html
import dash.dependencies as dd

from dash.exceptions import PreventUpdate
from flask import session
from flask_caching.backends import FileSystemCache
from more_itertools import unique_everseen


# region Make it possible for Output, Input, State to accept kwargs

class Input(dd.Input):
    def __init__(self, component_id, component_property, **kwargs):
        super().__init__(component_id, component_property)
        self.kwargs = kwargs


class State(dd.State):
    def __init__(self, component_id, component_property, **kwargs):
        super().__init__(component_id, component_property)
        self.kwargs = kwargs


class Output(dd.Output):
    def __init__(self, component_id, component_property, **kwargs):
        super().__init__(component_id, component_property)
        self.kwargs = kwargs


# endregion

# region Dash transformer


class DashTransformer(dash.Dash):

    def __init__(self, *args, transforms, **kwargs):
        super().__init__(*args, **kwargs)
        self.callbacks = []
        self.arg_types = [Output, Input, State]
        self.transforms = transforms
        # Do the transform initialization.
        for transform in self.transforms:
            transform.init(self)

    def callback(self, *args, **kwargs):
        """
         This method saves the callbacks on the DashTransformer object. It acts as a proxy for the Dash app callback.
        """
        # Parse Output/Input/State (could be made simpler by enforcing input structure)
        callback = {arg_type: [] for arg_type in self.arg_types}
        for arg in args:
            elements = _as_list(arg)
            for element in elements:
                for key in callback:
                    if isinstance(element, key):
                        callback[key].append(element)
        # Save the kwargs for later.
        callback["kwargs"] = kwargs
        # Save the callback for later.
        self.callbacks.append(callback)

        def wrapper(f):
            callback["f"] = f

        return wrapper

    def _layout_value(self):
        layout = self._layout() if self._layout_is_function else self._layout
        for transform in self.transforms:
            layout = transform.layout(layout, self._layout_is_function)
        return layout

    def _setup_server(self):
        """
         This method registers the callbacks on the Dash app and injects a session secret.
        """
        # Register the callbacks.
        callbacks = list(self._resolve_callbacks())
        for callback in callbacks:
            outputs = callback[Output][0] if len(callback[Output]) == 1 else callback[Output]
            super().callback(outputs, callback[Input], callback[State], **callback["kwargs"])(callback["f"])
        # Proceed as normally.
        super()._setup_server()
        # Set session secret. Used by some subclasses.
        if not self.server.secret_key:
            self.server.secret_key = secrets.token_urlsafe(16)

    def _resolve_callbacks(self):
        """
         This method resolves the callbacks, i.e. it applies the callback injections.
        """
        callbacks = self.callbacks
        for transform in self.transforms:
            callbacks = transform.apply(callbacks)
        return callbacks


def _get_session_id(session_key=None):
    session_key = "session_id" if session_key is None else session_key
    # Create unique session id.
    if not session.get(session_key):
        session[session_key] = secrets.token_urlsafe(16)
    return session.get(session_key)


def _as_list(item):
    if item is None:
        return []
    return item if isinstance(item, list) else [item]


def _create_callback_id(item):
    return "{}.{}".format(item.component_id, item.component_property)


class DashTransform:

    def init(self, dt):
        pass

    def apply(self, callbacks):
        raise NotImplementedError()

    def layout(self, layout, layout_is_function):
        return layout


# endregion

# region Trigger transform (the only default transform)

class Trigger(Input):
    """
     Like an Input, a trigger can trigger a callback, but it's values it not included in the resulting function call.
    """

    def __init__(self, component_id, component_property):
        super().__init__(component_id, component_property)


class TriggerTransform(DashTransform):

    def apply(self, callbacks):
        for callback in callbacks:
            is_trigger = [isinstance(item, Trigger) for item in callback[Input]]
            # Check if any triggers are there.
            if not any(is_trigger):
                continue
            # If so, filter the callback args.
            f = callback["f"]
            callback["f"] = filter_args(is_trigger)(f)
        return callbacks


def filter_args(args_filter):
    def wrapper(f):
        @functools.wraps(f)
        def decorated_function(*args):
            filtered_args = [arg for j, arg in enumerate(args) if not args_filter[j]]
            return f(*filtered_args)

        return decorated_function

    return wrapper


# endregion

# region Group transform

class GroupTransform(DashTransform):

    def apply(self, callbacks):
        groups = {}
        # Figure out which callbacks to group together.
        grouped_callbacks = []
        for i in range(len(callbacks)):
            key = callbacks[i]["kwargs"].pop("group", None)
            if key:
                if key not in groups:
                    groups[key] = []
                groups[key].append(i)
            else:
                grouped_callbacks.append(callbacks[i])
        # Do the grouping.
        for key in groups:
            grouped_callback = _combine_callbacks([callbacks[i] for i in groups[key]])
            grouped_callbacks.append(grouped_callback)

        return grouped_callbacks


# NOTE: No performance considerations what so ever. Just an initial proof-of-concept implementation.
def _combine_callbacks(callbacks):
    inputs, input_props, input_prop_lists, input_mappings = _prep_props(callbacks, Input)
    states, state_props, state_prop_lists, state_mappings = _prep_props(callbacks, State)
    outputs, output_props, output_prop_lists, output_mappings = _prep_props(callbacks, Output)
    # TODO: What kwargs to use?
    kwargs = callbacks[0]["kwargs"]

    # TODO: There might be a scope issue here
    def wrapper(*args):
        local_inputs = list(args)[:len(inputs)]
        local_states = list(args)[len(inputs):]
        if len(dash.callback_context.triggered) == 0:
            raise PreventUpdate
        prop_id = dash.callback_context.triggered[0]['prop_id']
        output_values = [dash.no_update] * len(outputs)
        for i, entry in enumerate(input_prop_lists):
            # Check if the trigger is an input of the callback.
            if prop_id not in entry:
                continue
            # Trigger the callback function.
            try:
                inputs_i = [local_inputs[j] for j in input_mappings[i]]
                states_i = [local_states[j] for j in state_mappings[i]]
                outputs_i = callbacks[i]["f"](*inputs_i, *states_i)
                if len(callbacks[i][Output]) == 1:
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

    return {Output: outputs, Input: inputs, "f": wrapper, State: states, "kwargs": kwargs}


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

# region Server side output transform

class ServersideOutput(Output):
    """
     Like a normal Output, but with the content stored only server side. Needs a backend for storing the data.
    """

    def __init__(self, component_id, component_property, backend=None, cache=None, session_check=None):
        super().__init__(component_id, component_property)
        if backend is None:
            backend = FileSystemStore()
        self.cache = cache
        self.backend = backend
        self.session_check = session_check


class ServersideOutputTransform(DashTransform):

    def __init__(self, backend=None, session_check=True):
        self.default_kwargs = dict(backend=backend, session_check=session_check)

    def init(self, dt):
        # Set session secret (if not already set).
        if not dt.server.secret_key:
            dt.server.secret_key = secrets.token_urlsafe(16)

    def apply(self, callbacks):
        # 1) Creat index.
        serverside_callbacks = []
        serverside_callback_kwargs = []
        serverside_output_map = {}
        for callback in callbacks:
            # Check if the callback targets server side outputs.
            serverside_output_kwargs = callback["kwargs"].pop("serverside_output", None)
            if not serverside_output_kwargs:
                continue
            # Keep tract of which outputs are server side outputs.
            serverside_outputs = []
            for output in callback[Output]:
                # Inject default kwargs.
                kwargs = output.kwargs
                for key in self.default_kwargs:
                    if key not in kwargs:
                        kwargs[key] = self.default_kwargs[key]
                # Convert to server side output.
                serverside_output = ServersideOutput(output.component_id, output.component_property, **kwargs)
                serverside_outputs.append(serverside_output)
                # Create map.
                serverside_output_map[_create_callback_id(output)] = serverside_output
            callback[Output] = serverside_outputs
            serverside_callbacks.append(callback)
            serverside_callback_kwargs.append(serverside_output_kwargs
                                              if isinstance(serverside_output_kwargs, dict) else {})
        # 2) Inject cached data into callbacks.
        for callback in callbacks:
            # Figure out which args need loading.
            items = callback[Input] + callback[State]
            item_ids = [_create_callback_id(item) for item in items]
            serverside_outputs = [serverside_output_map.get(item_id, None) for item_id in item_ids]
            # If any arguments are packed, unpack them.
            if any(serverside_outputs):
                f = callback["f"]
                callback["f"] = _unpack_outputs(serverside_outputs)(f)
        # 3) Apply the caching itself.
        for i, callback in enumerate(serverside_callbacks):
            f = callback["f"]
            callback["f"] = _pack_outputs(callback, **serverside_callback_kwargs[i])(f)
        return callbacks


def _unpack_outputs(serverside_outputs):
    def unpack(f):
        @functools.wraps(f)
        def decorated_function(*args):
            if not any(serverside_outputs):
                return f(*args)
            args = list(args)
            for i, serverside_output in enumerate(serverside_outputs):
                # Just skip elements that are not stored server side.
                if not serverside_output:
                    continue
                # Replace content of element(s).
                try:
                    args[i] = serverside_output.backend.get(args[i], ignore_expired=True)
                except TypeError as ex:
                    # TODO: Should we do anything about this?
                    args[i] = None
            return f(*args)

        return decorated_function

    return unpack


def _pack_outputs(callback, memoize=False):
    def packed_callback(f):
        @functools.wraps(f)
        def decorated_function(*args):
            multi_output = len(callback[Output]) > 1
            # If memoize is enabled, we check if the cache already has a valid value.
            if memoize:
                # Figure out if an update is necessary.
                unique_ids = []
                update_needed = False
                for i, output in enumerate(callback[Output]):
                    # Filter out Triggers (a little ugly to do here, should ideally be handled elsewhere).
                    args = [arg for i, arg in enumerate(args) if i > len(callback[Input]) or
                            not isinstance(callback[Input][i], Trigger)]
                    # Generate unique ID.
                    unique_id = _get_cache_id(f, output, list(args), output.session_check)
                    unique_ids.append(unique_id)
                    if not output.backend.has(unique_id):
                        update_needed = True
                        break
                # If not update is needed, just return the ids.
                if not update_needed:
                    return unique_ids if multi_output else unique_ids[0]
            # Do the update.
            data = f(*args)
            data = list(data) if multi_output else [data]
            for i, output in enumerate(callback[Output]):
                unique_id = _get_cache_id(f, output, list(args), output.session_check)
                output.backend.set(unique_id, data[i])
                data[i] = unique_id
            return data if multi_output else data[0]

        return decorated_function

    return packed_callback


def _get_cache_id(func, output, args, session_check=None):
    all_args = [func.__name__, _create_callback_id(output)] + list(args)
    if session_check:
        all_args += [_get_session_id()]
    return hashlib.md5(json.dumps(all_args).encode()).hexdigest()


# Interface definition for server stores.

class ServerStore:

    def get(self, key, ignore_expired=False):
        raise NotImplementedError()

    def set(self, key, value):
        raise NotImplementedError()

    def has(self, key):
        raise NotImplementedError()


# Place store implementations here.

class FileSystemStore(FileSystemCache):

    def __init__(self, cache_dir="file_system_store", **kwargs):
        super().__init__(cache_dir, **kwargs)

    def get(self, key, ignore_expired=False):
        if not ignore_expired:
            return super().get(key)
        # TODO: This part must be implemented for each type of cache.
        filename = self._get_filename(key)
        try:
            with open(filename, "rb") as f:
                pickle_time = pickle.load(f)  # ignore time
                return pickle.load(f)
        except (IOError, OSError, pickle.PickleError):
            return None


# endregion

# region No output transform

class NoOutputTransform(DashTransform):

    def __init__(self):
        self.initialized = False
        self.hidden_divs = []

    def layout(self, layout, layout_is_function):
        if layout_is_function or not self.initialized:
            children = layout.children + self.hidden_divs
            layout.children = children
            self.initialized = True
        return layout

    def apply(self, callbacks):
        for callback in callbacks:
            if len(callback[Output]) == 0:
                output_id = str(uuid.uuid4())
                hidden_div = html.Div(id=output_id, style={"display": "none"})
                callback[Output] = [Output(output_id, "children")]
                self.hidden_divs.append(hidden_div)
        return callbacks


# endregion

# region Transformer implementations

class Dash(DashTransformer):
    def __init__(self, *args, serverside_output_backend=None, session_check=True, **kwargs):
        transforms = [TriggerTransform(), NoOutputTransform(), GroupTransform(),
                      ServersideOutputTransform(serverside_output_backend, session_check)]
        super().__init__(*args, transforms=transforms, **kwargs)

# endregion
