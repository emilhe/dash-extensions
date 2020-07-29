import functools
import hashlib
import itertools
import json
import operator
import secrets
import dash
import uuid

import dash.dependencies as dd
import dash_html_components as html
from dash.exceptions import PreventUpdate
from flask import session
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

# # region Group transform
#
# class GroupTransform(DashTransform):
#
#     def apply(self, callbacks):
#         # Create callback groups.
#         groups = {}
#         for callback in callbacks:
#             if callback.kwargs and "group" in callback.kwargs:
#
#
#         # TODO: Implement
#         return callbacks
#
# # endregion

# region Cache transform

class CacheTransform(DashTransform):

    def __init__(self, cache=None, instant_refresh=True, session_check=True):
        self.default_args = dict(cache=cache, instant_refresh=instant_refresh, session_check=session_check)

    def init(self, dt):
        # Set session secret (if not already set).
        if not dt.server.secret_key:
            dt.server.secret_key = secrets.token_urlsafe(16)

    def apply(self, callbacks):
        # 1) Creat index what is to be cached.
        cached_callbacks = []
        callbacks_kwargs = []
        cached_output_ids = []
        output_kwargs = {}
        for callback in callbacks:
            callback_kwargs = []
            # Keep track of cached outputs.
            for output in callback[Output]:
                kwargs = output.kwargs
                # Check if caching is needed or not.
                if "cache" not in kwargs and not self.default_args["cache"]:
                    callback_kwargs.append(None)
                # Inject default args.
                for key in self.default_args:
                    kwargs[key] = kwargs[key] if key in kwargs else self.default_args[key]
                # Save stuff.
                output_id = _create_callback_id(output)
                cached_output_ids.append(output_id)
                output_kwargs[output_id] = kwargs
                callback_kwargs.append(kwargs)
            # Keep track of cached callbacks.
            if any(callback_kwargs):
                cached_callbacks.append(callback)
                callbacks_kwargs.append(callback_kwargs)
        # 2) Inject cached data into callbacks.
        for callback in callbacks:
            # Figure out which args need loading.
            items = callback[Input] + callback[State]
            item_ids = [_create_callback_id(item) for item in items]
            item_is_packed = [output_kwargs[item_id] if item_id in cached_output_ids else None for item_id in item_ids]
            # If any arguments are packed, unpack them.
            if any(item_is_packed):
                f = callback["f"]
                callback["f"] = _unpack_outputs(item_is_packed)(f)
        # 3) Apply the caching itself.
        for i, callback in enumerate(cached_callbacks):
            f = callback["f"]
            callback_kwargs = callbacks_kwargs[i]
            callback["f"] = _pack_outputs(callback[Output], callback_kwargs)(f)
        return callbacks


def _unpack_outputs(item_is_packed):
    def unpack(f):
        @functools.wraps(f)
        def decorated_function(*args):
            if not any(item_is_packed):
                return f(*args)
            args = list(args)
            for i, item in enumerate(item_is_packed):
                # Just skip elements that are not cached.
                if not item:
                    continue
                # Replace content of cached element(s).
                try:
                    args[i] = item["cache"].get(args[i])
                except TypeError:
                    args[i] = None
            return f(*args)

        return decorated_function

    return unpack


def _pack_outputs(outputs, output_kwargs):
    def packed_callback(f):
        @functools.wraps(f)
        def decorated_function(*args):
            update_needed = False
            multi_output = len(outputs) > 1
            unique_ids = []
            # Figure out if an update is necessary.
            for i, output in enumerate(outputs):
                kwargs = output_kwargs[i]
                # If any ouf the outputs are not cached (or needs instant refresh), we must reevaluate.
                if not kwargs or kwargs["instant_refresh"]:
                    update_needed = True
                    break
                # Check if item is already in the cache.
                unique_id = _get_cache_id(f, output, list(args), kwargs["session_check"])
                unique_ids.append(unique_id)
                if not kwargs["cache"].has(unique_id):
                    update_needed = True
                    break
            # If not update is needed, just return the ids.
            if not update_needed:
                return unique_ids
            # Do the update.
            data = f(*args)
            data = list(data) if multi_output else [data]
            for i, output in enumerate(outputs):
                kwargs = output_kwargs[i]
                if not kwargs:
                    continue
                unique_id = _get_cache_id(f, output, list(args), kwargs["session_check"])
                kwargs["cache"].set(unique_id, data[i])
                data[i] = unique_id
            return data if multi_output else data[0]

        return decorated_function

    return packed_callback


def _get_cache_id(func, output, args, session_check=None):
    all_args = [func.__name__, _create_callback_id(output)] + list(args)
    if session_check:
        all_args += [_get_session_id()]
    return hashlib.md5(json.dumps(all_args).encode()).hexdigest()


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
    def __init__(self, *args, cache=None, instant_refresh=True, session_check=True, **kwargs):
        transforms = [TriggerTransform(), NoOutputTransform(),
                      CacheTransform(cache, instant_refresh, session_check)]  # optimus prime includes ALL transforms
        super().__init__(*args, transforms=transforms, **kwargs)

# endregion
