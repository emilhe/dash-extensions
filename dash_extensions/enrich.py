import functools
import hashlib
import json
import logging
import pickle
import secrets
import uuid
from datetime import datetime

import plotly
import dash

# Enable enrich as drop-in replacement for dash
from dash import (
    no_update,
    Input,
    Output,
    State,
    ClientsideFunction,
    MATCH,
    ALL,
    ALLSMALLER,
    development,
    exceptions,
    resources,
    dcc,
    html,
    dash_table,
    callback_context,
    callback,
    clientside_callback,
)
from dash._utils import patch_collections_abc
from dash.dependencies import _Wildcard
from dash.development.base_component import Component
from flask import session
from flask_caching.backends import FileSystemCache, RedisCache
from more_itertools import flatten
from collections import defaultdict
from typing import Dict, Callable, List

_wildcard_mappings = {ALL: "<ALL>", MATCH: "<MATCH>", ALLSMALLER: "<ALLSMALLER>"}
_wildcard_values = list(_wildcard_mappings.values())


# region Dash blueprint

class DashBlueprint:
    def __init__(self, transforms=None, include_global_callbacks=False):
        self.callbacks = []
        self.clientside_callbacks = []
        self.arg_types = [Output, Input, State]
        self.transforms = _resolve_transforms(transforms)
        self._layout = None
        self._layout_is_function = False
        self.include_global_callbacks = include_global_callbacks
        # Do the transform initialization.
        for transform in self.transforms:
            transform.init(self)

    def _collect_callback(self, *args, **kwargs):
        """
        This method saves the callbacks on the DashTransformer object. It acts as a proxy for the Dash app callback.
        """
        # Parse Output/Input/State (could be made simpler by enforcing input structure)
        keys = ["output", "inputs", "state"]
        args = list(args) + list(flatten([_extract_list_from_kwargs(kwargs, key) for key in keys]))
        callback = {arg_type: [] for arg_type in self.arg_types}
        arg_order = []
        multi_output = False
        for arg in args:
            elements = _as_list(arg)
            for element in elements:
                for key in callback:
                    if isinstance(element, key):
                        # Check if this is a wild card output.
                        if not multi_output and isinstance(element, Output):
                            component_id = element.component_id
                            if isinstance(component_id, dict):
                                multi_output = any([component_id[k] in [ALLSMALLER, ALL] for k in component_id])
                        callback[key].append(element)
                        arg_order.append(element)
        if not multi_output:
            multi_output = len(callback[Output]) > 1
        # Save the kwargs for later.
        callback["kwargs"] = kwargs
        callback["sorted_args"] = arg_order
        callback["multi_output"] = multi_output

        return callback

    def callback(self, *args, **kwargs):
        """
        This method saves the callbacks on the DashTransformer object. It acts as a proxy for the Dash app callback.
        """
        callback = self._collect_callback(*args, **kwargs)
        self.callbacks.append(callback)

        def wrapper(f):
            callback["f"] = f

        return wrapper

    def clientside_callback(self, clientside_function, *args, **kwargs):
        callback = self._collect_callback(*args, **kwargs)
        callback["f"] = clientside_function
        self.clientside_callbacks.append(callback)

    def register_callbacks(self, app):
        callbacks, clientside_callbacks = self._resolve_callbacks()
        for cb in callbacks:
            outputs = cb[Output][0] if len(cb[Output]) == 1 else cb[Output]
            app.callback(outputs, cb[Input], cb[State], **cb["kwargs"])(cb["f"])
        for cb in clientside_callbacks:
            outputs = cb[Output][0] if len(cb[Output]) == 1 else cb[Output]
            app.clientside_callback(cb["f"], outputs, cb[Input], cb[State], **cb["kwargs"])

    def _resolve_callbacks(self):
        """
        This method resolves the callbacks, i.e. it applies the callback injections.
        """
        callbacks, clientside_callbacks = self.callbacks, self.clientside_callbacks
        # Add any global callbacks.
        if self.include_global_callbacks:
            callbacks += GLOBAL_BLUEPRINT.callbacks
            clientside_callbacks += GLOBAL_BLUEPRINT.clientside_callbacks
        # Proceed as before.
        for transform in self.transforms:
            callbacks, clientside_callbacks = transform.apply(callbacks, clientside_callbacks)
        return callbacks, clientside_callbacks

    # def register(self, app: dash.Dash, module, prefix=None, **kwargs):
    #     if prefix is not None:
    #         prefix_transform = PrefixIdTransform(prefix)
    #         self.transforms.append(prefix_transform)
    #         prefix_transform.init(self)
    #     self._register_callbacks(app)
    #     dash.register_page(module, layout=self._layout_value, **kwargs)

    def clear(self):
        self.callbacks = []
        self.clientside_callbacks = []
        self.arg_types = [Output, Input, State]
        self.transforms = []

    def _layout_value(self):
        layout = self._layout() if self._layout_is_function else self._layout
        for transform in self.transforms:
            layout = transform.layout(layout, self._layout_is_function)
        return layout

    @property
    def layout(self):
        return self._layout

    @layout.setter
    def layout(self, value):
        self._layout_is_function = isinstance(value, patch_collections_abc("Callable"))
        self._layout = value


# endregion

# region Dash proxy


class DashProxy(dash.Dash):
    def __init__(self, *args, transforms=None, include_global_callbacks=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.blueprint = DashBlueprint(transforms, include_global_callbacks=include_global_callbacks)

    def callback(self, *args, **kwargs):
        return self.blueprint.callback(*args, **kwargs)

    def clientside_callback(self, clientside_function, *args, **kwargs):
        return self.blueprint.clientside_callback(*args, **kwargs)

    def _setup_server(self):
        """
        This method registers the callbacks on the Dash app and injects a session secret.
        """
        # Register the callbacks.
        self.blueprint.register_callbacks(super())
        # Proceed as normally.
        super()._setup_server()
        # Set session secret. Used by some subclasses.
        if not self.server.secret_key:
            self.server.secret_key = secrets.token_urlsafe(16)

    def hijack(self, app: dash.Dash):
        # Change properties.
        app.config.update(self.config)
        app.title = self.title
        app.index_string = self.index_string
        # Inject layout.
        app.layout = html.Div()  # fool layout validator
        app._layout_value = self._layout_value
        # Register callbacks.
        self.blueprint.register_callbacks(app)
        # Setup secret.
        if not app.server.secret_key:
            app.server.secret_key = secrets.token_urlsafe(16)

    def _layout_value(self):
        """
        Delegate layout value (and property setter/getter) to blueprint.
        """
        return self.blueprint._layout_value()

    @property
    def layout(self):
        return self.blueprint._layout

    @layout.setter
    def layout(self, value):
        self.blueprint.layout = value


def _get_session_id(session_key=None):
    session_key = "session_id" if session_key is None else session_key
    # Create unique session id.
    if not session.get(session_key):
        session[session_key] = secrets.token_urlsafe(16)
    return session.get(session_key)


def _extract_list_from_kwargs(kwargs: dict, key: str) -> list:
    if kwargs is not None and key in kwargs:
        contents = kwargs.pop(key)
        if contents is None:
            return []
        if isinstance(contents, list):
            return contents
        else:
            return [contents]
    else:
        return []


# endregion

# region Dash transform

class DashTransform:
    def __init__(self):
        self.layout_initialized = False

    def init(self, dt):
        pass

    def apply(self, callbacks, clientside_callbacks):
        return self.apply_serverside(callbacks), self.apply_clientside(clientside_callbacks)

    def apply_serverside(self, callbacks):
        return callbacks  # per default do nothing

    def apply_clientside(self, callbacks):
        return callbacks  # per default do nothing

    def layout(self, layout, layout_is_function):
        if layout_is_function or not self.layout_initialized:
            self.transform_layout(layout)
            self.layout_initialized = True
        return layout

    def transform_layout(self, layout):
        return layout  # per default, do nothing

    def get_dependent_transforms(self):
        return []

    def sort_key(self):
        return 1


def _resolve_transforms(transforms: List[DashTransform]) -> List[DashTransform]:
    # Resolve transforms.
    transforms = [] if transforms is None else transforms
    dependent_transforms = []
    for transform in transforms:
        for dependent_transform in transform.get_dependent_transforms():
            # Check if the dependent transform is already there.
            if any([isinstance(t, dependent_transform.__class__) for t in transforms]):
                continue
                # Otherwise, add it.
            dependent_transforms.append(dependent_transform)
    return sorted(transforms + dependent_transforms, key=lambda t: t.sort_key())


# endregion

# region Blocking callback transform


class BlockingCallbackTransform(DashTransform):
    def __init__(self, timeout=60):
        super().__init__()
        self.components = []
        self.blueprint = DashBlueprint()
        self.timeout = timeout

    def transform_layout(self, layout):
        children = _as_list(layout.children) + self.components
        layout.children = children

    def apply(self, callbacks, clientside_callbacks):
        callbacks = self.apply_serverside(callbacks)
        return callbacks, clientside_callbacks + self.blueprint.clientside_callbacks

    def apply_serverside(self, callbacks):
        for callback in callbacks:
            if not callback["kwargs"].get("blocking", None):
                continue

            timeout = callback["kwargs"].get("blocking_timeout", self.timeout)
            callback_id = _get_output_id(callback)
            # Bind proxy components.
            start_client_id = f"{callback_id}_start_client"
            end_server_id = f"{callback_id}_end_server"
            end_client_id = f"{callback_id}_end_client"
            self.components.extend(
                [dcc.Store(id=start_client_id), dcc.Store(id=end_server_id), dcc.Store(id=end_client_id)]
            )
            # Bind start signal callback.
            start_callback = f"""function()
            {{
                const start = arguments[arguments.length-2];
                const end = arguments[arguments.length-1];
                const now = new Date().getTime();
                if(!end & !start){{
                    return now;
                }}
                if((now - start)/1000 > {timeout}){{              
                    console.log("HITTING TIMEOUT");  
                    return now;
                }}
                if(!end){{
                    return window.dash_clientside.no_update;
                }}
                if(end > start){{
                    return now;
                }}
                return window.dash_clientside.no_update;
            }}"""
            self.blueprint.clientside_callback(
                start_callback,
                Output(start_client_id, "data"),
                callback[Input],
                [State(start_client_id, "data"), State(end_client_id, "data")],
            )
            # Bind end signal callback.
            self.blueprint.clientside_callback(
                "function(){return new Date().getTime();}", Output(end_client_id, "data"), Input(end_server_id, "data")
            )
            # Modify the original callback to send finished signal.
            callback[Output].append(Output(end_server_id, "data"))
            # Modify the original callback to not trigger on inputs, but the new special trigger.
            new_state = [State(item.component_id, item.component_property) for item in callback[Input]]
            callback[State] = new_state + callback[State]
            callback[Input] = [Input(start_client_id, "data")]
            # Modify the callback function accordingly.
            f = callback["f"]
            callback["f"] = skip_input_signal_add_output_signal()(f)

        return callbacks


def skip_input_signal_add_output_signal():
    def wrapper(f):
        @functools.wraps(f)
        def decorated_function(*args):
            value = f(*args[1:])
            return _as_list(value) + [datetime.utcnow().timestamp()]

        return decorated_function

    return wrapper


# endregion

# region Log transform


class LogConfig:
    def __init__(self, log_output, log_writer_map: Dict[int, Callable]):
        self.log_output = log_output
        self.log_writer_map = log_writer_map


def setup_notifications_log_config(layout: List[Component]):
    import dash_mantine_components as dmc

    layout.append(dmc.NotificationsProvider(id="notifications_provider"))
    log_output = Output("notifications_provider", "children")
    return LogConfig(log_output, get_notification_log_writers())


def setup_div_log_config(layout: List[Component]):
    layout.append(html.Div(id="log"))
    log_output = Output("log", "children")
    return LogConfig(log_output, get_default_log_writers())


def get_default_log_writers():
    return {
        logging.INFO: lambda x, **kwargs: html.Div(f"INFO: {x}", **kwargs),
        logging.WARNING: lambda x, **kwargs: html.Div(f"WARNING: {x}", **kwargs),
        logging.ERROR: lambda x, **kwargs: html.Div(f"ERROR: {x}", **kwargs),
    }


def get_notification_log_writers():
    import dash_mantine_components as dmc

    def _default_kwargs(color, title, message):
        return dict(color=color, title=title, message=message, id=str(uuid.uuid4()), action="show", autoClose=False)

    def log_info(message, **kwargs):
        return dmc.Notification(**{**_default_kwargs("blue", "Info", message), **kwargs})

    def log_warning(message, **kwargs):
        return dmc.Notification(**{**_default_kwargs("yellow", "Warning", message), **kwargs})

    def log_error(message, **kwargs):
        return dmc.Notification(**{**_default_kwargs("red", "Error", message), **kwargs})

    return {logging.INFO: log_info, logging.WARNING: log_warning, logging.ERROR: log_error}


class DashLogger:
    def __init__(self, log_writers: Dict[int, Callable]):
        self.log_writers = log_writers
        self.output = []

    def clear(self):
        self.output.clear()

    def info(self, message, **kwargs):
        self.log(logging.INFO, message, **kwargs)

    def warning(self, message, **kwargs):
        self.log(logging.WARNING, message, **kwargs)

    def error(self, message, **kwargs):
        self.log(logging.ERROR, message, **kwargs)

    def log(self, level, message, **kwargs):
        self.output.append(self.log_writers[level](message, **kwargs))

    def get_output(self):
        return self.output if self.output else dash.no_update


class LogTransform(DashTransform):
    def __init__(self, log_config=None):
        super().__init__()
        self.components = []
        if log_config is None:
            # If no config is provided, try to use dmc notification system.
            try:
                # raise ImportError
                log_config = setup_notifications_log_config(self.components)
            # If dmc is not installed, use a div.
            except ImportError:
                msg = "Failed to import dash-mantine-components, falling back to simple div for log output."
                logging.warning(msg)
                log_config = setup_div_log_config(self.components)
        self.log_config = log_config

    def transform_layout(self, layout):
        children = _as_list(layout.children) + self.components
        layout.children = children

    def apply(self, callbacks, clientside_callbacks):
        callbacks = self.apply_serverside(callbacks)
        return callbacks, clientside_callbacks

    def apply_serverside(self, callbacks):
        for callback in callbacks:
            if not callback["kwargs"].get("log", None):
                continue
            # Add the log component as output.
            callback[Output].append(self.log_config.log_output)
            # Modify the callback function accordingly.
            f = callback["f"]
            logger = DashLogger(self.log_config.log_writer_map)  # TODO: What about scope?
            callback["f"] = bind_logger(logger)(f)

        return callbacks

    def get_dependent_transforms(self):
        return [MultiplexerTransform()]


def bind_logger(logger):
    def wrapper(f):
        @functools.wraps(f)
        def decorated_function(*args):
            logger.clear()
            value = f(*args, logger)
            return _as_list(value) + [logger.get_output()]

        return decorated_function

    return wrapper


# endregion

# region Global blueprint object (to emulate Dash 2.0 import syntax)

GLOBAL_BLUEPRINT = DashBlueprint()


def callback(*args, **kwargs):
    return GLOBAL_BLUEPRINT.callback(*args, **kwargs)


def clientside_callback(clientside_function, *args, **kwargs):
    return GLOBAL_BLUEPRINT.clientside_callback(clientside_function, *args, **kwargs)


# endregion

# region Prefix ID transform


class PrefixIdTransform(DashTransform):
    def __init__(self, prefix, prefix_func=None):
        super().__init__()
        self.prefix = prefix
        self.prefix_func = prefix_func if prefix_func is not None else prefix_component

    def _apply(self, callbacks):
        for callback in callbacks:
            for arg in callback["sorted_args"]:
                arg.component_id = apply_prefix(self.prefix, arg.component_id)
        return callbacks

    def apply_serverside(self, callbacks):
        return self._apply(callbacks)

    def apply_clientside(self, callbacks):
        return self._apply(callbacks)

    def transform_layout(self, layout):
        prefix_recursively(layout, self.prefix, self.prefix_func)


def apply_prefix(prefix, component_id):
    if isinstance(component_id, dict):
        for key in component_id:
            # This branch handles the IDs. TODO: Can we always assume use of ints?
            if type(component_id[key]) == int:
                continue
            # This branch handles the wildcard callbacks.
            if isinstance(component_id[key], _Wildcard):
                continue
            # All "normal" props are prefixed.
            component_id[key] = "{}-{}".format(prefix, component_id[key])
        return component_id
    return "{}-{}".format(prefix, component_id)


def prefix_recursively(item, key, prefix_func):
    prefix_func(key, item)
    if hasattr(item, "children"):
        children = _as_list(item.children)
        for child in children:
            prefix_recursively(child, key, prefix_func)


def prefix_component(key, component):
    if hasattr(component, "id"):
        component.id = apply_prefix(key, component.id)
    if not hasattr(component, "_namespace"):
        return
    # Special handling of dash bootstrap components. TODO: Maybe add others?
    if component._namespace == "dash_bootstrap_components":
        if component._type == "Tooltip":
            component.target = apply_prefix(key, component.target)


# endregion

# region Trigger transform (the only default transform)


class Trigger(Input):
    """
    Like an Input, a trigger can trigger a callback, but it's values it not included in the resulting function call.
    """

    def __init__(self, component_id, component_property):
        super().__init__(component_id, component_property)


class TriggerTransform(DashTransform):

    # NOTE: This transform cannot be implemented for clientside callbacks since the JS can't be modified from here.

    def apply_serverside(self, callbacks):
        for callback in callbacks:
            is_trigger = trigger_filter(callback["sorted_args"])
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
            post_args = list(args[len(args_filter):])
            args = list(args[: len(args_filter)])
            filtered_args = [arg for j, arg in enumerate(args) if not args_filter[j]] + post_args
            return f(*filtered_args)

        return decorated_function

    return wrapper


def trigger_filter(args):
    inputs_args = [item for item in args if isinstance(item, Input) or isinstance(item, State)]
    is_trigger = [isinstance(item, Trigger) for item in inputs_args]
    return is_trigger


# endregion

# region Multiplexer transform


def _mp_id(output: Output, idx: int) -> Dict[str, str]:
    if isinstance(output.component_id, dict):
        return {**output.component_id, **dict(prop=output.component_property, idx=idx)}
    return dict(id=output.component_id, prop=output.component_property, idx=idx)


def _escape_wildcards(mp_id):
    if not isinstance(mp_id, dict):
        return mp_id
    for key in mp_id:
        # The ALL wildcard is supported.
        if mp_id[key] == ALL:
            mp_id[key] = _wildcard_mappings[ALL]
            continue
        # Other ALL wildcards are NOT supported.
        if mp_id[key] in _wildcard_mappings:
            raise ValueError(f"Multiplexer does not support wildcard [{mp_id[key]}]")
    return mp_id


def _mp_element(mp_id: Dict[str, str]) -> dcc.Store:
    return dcc.Store(id=mp_id)


def _mp_prop() -> str:
    return "data"


def inject_proxies_recursively(node, proxy_map):
    if not hasattr(node, "children") or node.children is None:
        return
    children = _as_list(node.children)
    modified = False
    for i, child in enumerate(children):
        # Do recursion.
        inject_proxies_recursively(child, proxy_map)
        # Attach the proxy components as children of the original component to ensure dcc.Loading works.
        if not hasattr(child, "id"):
            continue
        for key in proxy_map:
            if not child.id == key:
                continue
            children[i] = html.Div([child] + proxy_map[key])
            modified = True
    if modified:
        node.children = children


class MultiplexerTransform(DashTransform):
    """
    The MultiplexerTransform makes it possible to target an output by callbacks multiple times. Under the hood, proxy
    components (dcc.Store) are used, and the proxy_location keyword argument determines where these proxies are placed.
    The default value "inplace" means that the original component is replace by a Div element that wraps the original
    component and its proxies. The means that dcc.Loading will work, but it also means that if you replace the layout
    of a component higher in the tree in a callback, you might end up deleting the proxies (!), which will break your
    app. For this particular case, you can set proxy_location to a custom component (or None to use the layout root),
    to place the proxies here instead. To use dcc.Loading for this particular case, the proxy_location must be wrapped.
    """

    def __init__(self, proxy_location=None, proxy_wrapper_map=None):
        super().__init__()
        self.proxy_location = proxy_location
        self.proxy_map = defaultdict(lambda: [])
        self.proxy_wrapper_map = proxy_wrapper_map
        self.blueprint = DashBlueprint()

    def transform_layout(self, layout):
        # Apply wrappers if needed.
        if self.proxy_wrapper_map:
            for key in self.proxy_wrapper_map:
                if key in self.proxy_map:
                    self.proxy_map[key] = _as_list(self.proxy_wrapper_map[key](self.proxy_map[key]))
        # Inject proxies in a user defined component.
        if self.proxy_location == "inplace":
            inject_proxies_recursively(layout, self.proxy_map)
        # Inject proxies in a component, either user defined or top level.
        else:
            target = self.proxy_location if isinstance(self.proxy_location, Component) else layout
            proxies = list(flatten(list(self.proxy_map.values())))
            target.children = _as_list(target.children) + proxies

    def apply(self, callbacks, clientside_callbacks):
        all_callbacks = callbacks + clientside_callbacks
        # Group by output.
        output_map = defaultdict(list)
        for callback in all_callbacks:
            for output in callback[Output]:
                output_map[output].append(callback)
        # Apply multiplexer where needed.
        for output in output_map:
            # If there is only one output, multiplexing is not needed.
            if len(output_map[output]) == 1:
                continue
            self._apply_multiplexer(output, output_map[output])

        return callbacks, clientside_callbacks + self.blueprint.clientside_callbacks

    def _apply_multiplexer(self, output, callbacks):
        inputs = []
        proxies = []
        for i, callback in enumerate(callbacks):
            mp_id = _mp_id(output, i)
            mp_id_escaped = _escape_wildcards(mp_id)
            # Create proxy element.
            proxies.append(_mp_element(mp_id_escaped))
            # Assign proxy element as output.
            callback[Output][callback[Output].index(output)] = Output(mp_id_escaped, _mp_prop())
            # Create proxy input.
            inputs.append(Input(mp_id, _mp_prop()))
        # Collect proxy elements to add to layout.
        self.proxy_map[output].extend(proxies)
        # Create multiplexer callback. Clientside for best performance. TODO: Is this robust?
        self.blueprint.clientside_callback(
            """
            function(){
                const ts = dash_clientside.callback_context.triggered;
                return ts[0].value;
            }
        """,
            output,
            inputs,
            prevent_initial_call=True,
        )

    def sort_key(self):
        return 10


# endregion

# region Server side output transform


class EnrichedOutput(Output):
    """
    Like a normal Output, includes additional properties related to storing the data.
    """

    def __init__(self, component_id, component_property, backend=None, session_check=None, arg_check=True):
        super().__init__(component_id, component_property)
        self.backend = backend
        self.session_check = session_check
        self.arg_check = arg_check


class ServersideOutput(EnrichedOutput):
    """
    Like a normal Output, but with the content stored only server side.
    """


class ServersideOutputTransform(DashTransform):
    def __init__(self, backend=None, session_check=True, arg_check=True):
        super().__init__()
        self.backend = backend if backend is not None else FileSystemStore()
        self.session_check = session_check
        self.arg_check = arg_check

    def init(self, dt):
        # Set session secret (if not already set).
        if not dt.server.secret_key:
            dt.server.secret_key = secrets.token_urlsafe(16)

    # NOTE: Doesn't make sense for clientside callbacks.

    def apply_serverside(self, callbacks):
        # 1) Create index.
        serverside_callbacks = []
        serverside_output_map = {}
        for callback in callbacks:
            # If memoize keyword is used, serverside caching is needed.
            memoize = callback["kwargs"].get("memoize", None)
            serverside = False
            # Keep tract of which outputs are server side outputs.
            for output in callback[Output]:
                if isinstance(output, ServersideOutput):
                    serverside_output_map[_create_callback_id(output)] = output
                    serverside = True
                # Set default values.
                if not isinstance(output, ServersideOutput) and not memoize:
                    continue
                output.backend = output.backend if output.backend is not None else self.backend
                output.arg_check = output.arg_check if output.arg_check is not None else self.arg_check
                output.session_check = output.session_check if output.session_check is not None else self.session_check
            # Keep track of server side callbacks.
            if serverside or memoize:
                serverside_callbacks.append(callback)
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
            callback["f"] = _pack_outputs(callback)(f)
        # 4) Strip special args.
        for callback in callbacks:
            for key in ["memoize"]:
                callback["kwargs"].pop(key, None)

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


def _pack_outputs(callback):
    memoize = callback["kwargs"].get("memoize", None)

    def packed_callback(f):
        @functools.wraps(f)
        def decorated_function(*args):
            multi_output = callback["multi_output"]
            # If memoize is enabled, we check if the cache already has a valid value.
            if memoize:
                # Figure out if an update is necessary.
                unique_ids = []
                update_needed = False
                for i, output in enumerate(callback[Output]):
                    # Filter out Triggers (a little ugly to do here, should ideally be handled elsewhere).
                    is_trigger = trigger_filter(callback["sorted_args"])
                    filtered_args = [arg for i, arg in enumerate(args) if not is_trigger[i]]
                    # Generate unique ID.
                    unique_id = _get_cache_id(f, output, list(filtered_args), output.session_check, output.arg_check)
                    unique_ids.append(unique_id)
                    if not output.backend.has(unique_id):
                        update_needed = True
                        break
                # If not update is needed, just return the ids (or values, if not serverside output).
                if not update_needed:
                    results = [
                        uid
                        if isinstance(callback[Output][i], ServersideOutput)
                        else callback[Output][i].backend.get(uid)
                        for i, uid in enumerate(unique_ids)
                    ]
                    return results if multi_output else results[0]
            # Do the update.
            data = f(*args)
            data = list(data) if multi_output else [data]
            if callable(memoize):
                data = memoize(data)
            for i, output in enumerate(callback[Output]):
                # Skip no_update updates.
                if isinstance(data[i], type(no_update)):
                    continue
                # Replace only for server side outputs.
                serverside_output = isinstance(callback[Output][i], ServersideOutput)
                if serverside_output or memoize:
                    # Filter out Triggers (a little ugly to do here, should ideally be handled elsewhere).
                    is_trigger = trigger_filter(callback["sorted_args"])
                    filtered_args = [arg for i, arg in enumerate(args) if not is_trigger[i]]
                    unique_id = _get_cache_id(f, output, list(filtered_args), output.session_check, output.arg_check)
                    output.backend.set(unique_id, data[i])
                    # Replace only for server side outputs.
                    if serverside_output:
                        data[i] = unique_id
            return data if multi_output else data[0]

        return decorated_function

    return packed_callback


def _get_cache_id(func, output, args, session_check=None, arg_check=True):
    all_args = [func.__name__, _create_callback_id(output)]
    if arg_check:
        all_args += list(args)
    if session_check:
        all_args += [_get_session_id()]
    return hashlib.md5(json.dumps(all_args).encode()).hexdigest()


def _get_output_id(callback):
    if isinstance(callback["f"], (ClientsideFunction, str)):
        f_repr = repr(callback["f"])  # handles clientside functions
    else:
        f_repr = f"{callback['f'].__module__}.{callback['f'].__name__}"  # handles Python functions
    f_hash = hashlib.md5(f_repr.encode()).digest()
    return str(uuid.UUID(bytes=f_hash, version=4))


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


class RedisStore(RedisCache):
    """
    Store that uses Redis as backend. Note, that the timeout must be large enough that a (k,v) pair NEVER expires
    during a user session. If it does, the user experience for those sessions will be degraded.
    """

    def __init__(self, default_timeout=24 * 3600, **kwargs):
        super().__init__(default_timeout=default_timeout, **kwargs)

    def get(self, key, ignore_expired=False):
        # TODO: Is there any way to honor ignore_expired for redis? I don't think so
        return super().get(key)


# endregion

# region No output transform


class NoOutputTransform(DashTransform):
    def __init__(self):
        super().__init__()
        self.components = []

    def transform_layout(self, layout):
        children = _as_list(layout.children) + self.components
        layout.children = children

    def _apply(self, callbacks):
        for callback in callbacks:
            if len(callback[Output]) == 0:
                output_id = _get_output_id(callback)
                hidden_div = html.Div(id=output_id, style={"display": "none"})
                callback[Output] = [Output(output_id, "children")]
                self.components.append(hidden_div)
        return callbacks

    def apply_serverside(self, callbacks):
        return self._apply(callbacks)

    def apply_clientside(self, callbacks):
        return self._apply(callbacks)

    def sort_key(self):
        return 0


# endregion

# region Batteries included dash proxy object


class Dash(DashProxy):
    def __init__(self, *args, output_defaults=None, **kwargs):
        output_defaults = dict(backend=None, session_check=True) if output_defaults is None else output_defaults
        transforms = [
            TriggerTransform(),
            LogTransform(),
            MultiplexerTransform(),
            NoOutputTransform(),
            ServersideOutputTransform(**output_defaults),
        ]
        super().__init__(*args, transforms=transforms, **kwargs)


# endregion

# region Utils

def _as_list(item):
    if item is None:
        return []
    if isinstance(item, tuple):
        return list(item)
    if isinstance(item, list):
        return item
    return [item]


def _create_callback_id(item):
    cid = item.component_id
    if isinstance(cid, dict):
        cid = {key: cid[key] if cid[key] not in _wildcard_mappings else _wildcard_mappings[cid[key]] for key in cid}
        cid = json.dumps(cid)
    return "{}.{}".format(cid, item.component_property)


def plotly_jsonify(data):
    return json.loads(json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder))

# endregion
