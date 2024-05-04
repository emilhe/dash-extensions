from __future__ import annotations

import dataclasses
import functools
import hashlib
import inspect
import json
import logging
import secrets
import struct
import sys
import threading
import uuid
import plotly
import dash

# Enable enrich as drop-in replacement for dash
# noinspection PyUnresolvedReferences
from dash import (  # lgtm [py/unused-import]
    no_update,
    Output,
    State,
    Input,
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
    page_container,
    page_registry,
    register_page,
    ctx
)
from dash._callback_context import context_value
from dash._utils import patch_collections_abc
from dash.dependencies import _Wildcard, DashDependency  # lgtm [py/unused-import]
from dash.development.base_component import Component
from flask import session
from flask_caching.backends import FileSystemCache, RedisCache
from itertools import compress
from more_itertools import flatten
from collections import defaultdict
from typing import Dict, Callable, List, Union, Any, Tuple, Optional, Generic, TypeVar
from datetime import datetime
from dash_extensions import CycleBreaker
from dataclass_wizard import fromdict, asdict

T = TypeVar("T")

_wildcard_mappings = {ALL: "<ALL>", MATCH: "<MATCH>", ALLSMALLER: "<ALLSMALLER>"}
_wildcard_values = list(_wildcard_mappings.values())

DEPENDENCY_APPEND_PREFIX = "dash_extensions_"


# region DependencyCollection

def build_index(structure, entry, index):
    if isinstance(structure, list):
        for i, s in enumerate(structure):
            build_index(s, entry + [i], index)
        return index
    if isinstance(structure, dict):
        for k in structure:
            build_index(structure[k], entry + [k], index)
        return index
    if isinstance(structure, DashDependency):
        index.append(entry)
        return index
    raise ValueError(f"Unsupported structure {str(structure)}")


def validate_structure(structure, level=0):
    if isinstance(structure, DashDependency):
        if level == 0:
            return [structure]
        return structure
    if isinstance(structure, tuple):
        result = list(structure)
        for i, entry in enumerate(result):
            result[i] = validate_structure(entry, level=level + 1)
        return result
    if isinstance(structure, list):
        for i, entry in enumerate(structure):
            structure[i] = validate_structure(entry, level=level + 1)
        return structure
    if isinstance(structure, dict):
        for k in structure:
            structure[k] = validate_structure(structure[k], level=level + 1)
        return structure
    raise ValueError(f"Unsupported structure {structure}")


class DependencyCollection:
    def __init__(self, structure, keyword=None):
        self.structure = validate_structure(structure)
        self.keyword = keyword
        self._index = None
        self._re_index()

    def __getitem__(self, key: int):
        return self.get(self._index[key])

    def __setitem__(self, key: int, value):
        return self.set(self._index[key], value)

    def __len__(self):
        return len(self._index)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def index(self, value):
        for i in range(len(self)):
            if self[i] == value:
                return i
        return -1

    def get(self, multi_index):
        e = self.structure
        for j in multi_index:
            e = e[j]
        return e

    def set(self, multi_index, value):
        e = self.structure
        for i, j in enumerate(multi_index):
            if i == len(multi_index) - 1:
                e[j] = value

    def append(self, value, flex_key=None, index=None):
        i = len(self._index)
        if isinstance(self.structure, list):
            if index is not None:
                self.structure.insert(index, value)
                self._re_index()
                return index
            else:
                self.structure.append(value)
                self._re_index()
                return i
        if isinstance(self.structure, dict):
            flex_key = f"{DEPENDENCY_APPEND_PREFIX}{i}" if flex_key is None else flex_key
            self.structure[flex_key] = value
            self._re_index()
            return flex_key

    def _re_index(self):
        self._index = build_index(self.structure, [], [])


# endregion

# region Dash blueprint

def collect_args(args: Union[Tuple[Any], List[Any]], inputs, outputs):
    for arg in args:
        if isinstance(arg, (list, tuple)):
            collect_args(arg, inputs, outputs)
            continue
        if isinstance(arg, Output):
            outputs.append(arg)
            continue
        if isinstance(arg, (Input, State)):
            inputs.append(arg)
            continue
        # If we get here, the argument was not recognized.
        raise ValueError(f"Unsupported argument: {arg}")
    return DependencyCollection(inputs), DependencyCollection(outputs)


class DummyDependency(DashDependency):
    """
    Object used to represent dummy dependencies.
    """

    def __init__(self, component_id, component_property):
        super().__init__(component_id, component_property)


class CallbackBlueprint:
    def __init__(self, *args, **kwargs):
        # Collect args "normally".
        self.inputs, self.outputs = collect_args(args, [], [])
        # Flexible signature handling via keyword arguments. If provided, it takes precedence.
        if "output" in kwargs:
            self.outputs = DependencyCollection(kwargs.pop("output"), keyword="output")
        if "inputs" in kwargs:
            self.inputs = DependencyCollection(kwargs.pop("inputs"), keyword="inputs")
        if "state" in kwargs:
            raise ValueError("Please use the 'inputs' keyword instead of the 'state' keyword.")
        # Collect dummy elements.
        if kwargs.get("background", False) and "progress" in kwargs:
            # This element represents the set_progress function.
            self.inputs.append(DummyDependency("function", "set_progress"), index=0, flex_key="set_progress")
        # Collect the rest.
        self.kwargs: Dict[str, Any] = kwargs
        self.f = None

    def register(self, app: dash.Dash):
        # Collect dependencies.
        dep_args, dep_kwargs = [], {}
        for dep_col in [self.outputs, self.inputs]:
            s = dep_col.structure
            if isinstance(s, list) and len(s) == 1:
                s = s[0]
            if isinstance(s, DummyDependency):
                continue
            if isinstance(s, list):
                s = [dep for dep in s if not isinstance(dep, DummyDependency)]
            if dep_col.keyword is None:
                dep_args.append(s)
            else:
                dep_kwargs[dep_col.keyword] = s
        # Do binding.
        if isinstance(self.f, (str, ClientsideFunction)):
            app.clientside_callback(self.f, *dep_args, **dep_kwargs, **self.kwargs)
        else:
            app.callback(*dep_args, **dep_kwargs, **self.kwargs)(self.f)

    @property
    def uid(self) -> str:
        if isinstance(self.f, (ClientsideFunction, str)):
            f_repr = repr(self.f)  # handles clientside functions
        else:
            f_repr = f"{self.f.__module__}.{self.f.__name__}"  # handles Python functions
        f_hash = hashlib.md5(f_repr.encode()).digest()
        return str(uuid.UUID(bytes=f_hash, version=4))

    @property
    def multi_output(self) -> bool:
        # Check if there are more than  1 output.
        if len(self.outputs) > 1:
            return True
        # Check for wild card output(s).
        component_id = self.outputs[0].component_id
        if not isinstance(component_id, dict):
            return False
        # The ALL and ALLSMALLER flags indicate multi output.
        return any([component_id[k] in [ALLSMALLER, ALL] for k in component_id])


class DashBlueprint:
    def __init__(self, transforms: List[DashTransform] = None, include_global_callbacks: bool = False):
        self.callbacks: List[CallbackBlueprint] = []
        self.clientside_callbacks: List[CallbackBlueprint] = []
        self.transforms = _resolve_transforms(transforms)
        self._layout = None
        self._layout_is_function = False
        self.include_global_callbacks = include_global_callbacks

    def callback(self, *args, **kwargs):
        """
        This method saves the callback on the DashBlueprint object.
        """
        cbp = CallbackBlueprint(*args, **kwargs)
        self.callbacks.append(cbp)

        def wrapper(f):
            cbp.f = f
            return f

        return wrapper

    def clientside_callback(self, clientside_function, *args, **kwargs):
        """
        This method saves the clientside callback on the DashBlueprint object.
        """
        cbp = CallbackBlueprint(*args, **kwargs)
        cbp.f = clientside_function
        self.clientside_callbacks.append(cbp)

    def register_callbacks(self, app: Union[dash.Dash, DashBlueprint]):
        """
        This function registers all callbacks collected by the blueprint onto a Dash (or DashBlueprint) object.
        """
        callbacks, clientside_callbacks = self._resolve_callbacks()
        # Move callbacks from one blueprint to another.
        if isinstance(app, DashProxy):
            app.blueprint.callbacks += callbacks
            app.blueprint.clientside_callbacks += clientside_callbacks
            return
        # Register callbacks on the "real" app object.
        for cbp in callbacks + clientside_callbacks:
            cbp.register(app)

    def _resolve_callbacks(self) -> Tuple[List[CallbackBlueprint], List[CallbackBlueprint]]:
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

    # TODO: Include or not? The plugin still seems a bit immature.
    def register(self, app: Union[dash.Dash, DashProxy], module, prefix: Union[str, PrefixIdTransform, None]=None, **kwargs):      
        # Add prefix transform if supplied.
        if prefix is not None:
            prefix_transform = prefix if isinstance(prefix, PrefixIdTransform) else PrefixIdTransform(prefix)
            self.transforms.append(prefix_transform)                                          
        # Register the callbacks and page.
        self.register_callbacks(app)
        dash.register_page(module, layout=self._layout_value, **kwargs)
    
    def clear(self):
        self.callbacks = []
        self.clientside_callbacks = []
        self.transforms = []

    def _layout_value(self, *args, **kwargs):
        layout = self._layout(*args, **kwargs) if self._layout_is_function else self._layout
        for transform in self.transforms:
            layout = transform.layout(layout, self._layout_is_function)
        return layout

    def embed(self, app: DashProxy):
        if app.blueprint._layout_is_function and app._got_first_request["setup_server"]:
            return self._layout_value()
        self.register_callbacks(app)
        return self._layout_value()

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
    """
    DashProxy is a wrapper around the DashBlueprint object enabling drop-in replacement of the original Dash object. It
    enables transforms (via the DashBlueprint object), performs the necessary app configuration for all transforms to
    work (e.g. setting a secret key on the server), and exposes convenience functions such as 'hijack'.
    """

    def __init__(self, *args, transforms=None, include_global_callbacks=True, blueprint=None,
                 prevent_initial_callbacks="initial_duplicate", **kwargs):
        super().__init__(*args, prevent_initial_callbacks=prevent_initial_callbacks, **kwargs)
        self.blueprint = DashBlueprint(transforms,
                                       include_global_callbacks=include_global_callbacks) if blueprint is None else blueprint
        self.setup_server_lock = threading.Lock()

    def callback(self, *args, **kwargs):
        return self.blueprint.callback(*args, **kwargs)

    def clientside_callback(self, clientside_function, *args, **kwargs):
        return self.blueprint.clientside_callback(clientside_function, *args, **kwargs)

    def long_callback(self, *_args, **_kwargs):
        raise NotImplementedError(
            "The 'long_callback(..)' syntax is not supported, please use 'callback(background=True, ...)' instead.")

    def register_celery_tasks(self):
        if sys.argv[0].endswith("celery"):
            self.register_callbacks()

    def register_callbacks(self):
        self.blueprint.register_callbacks(super())

    def _setup_server(self):
        with self.setup_server_lock:
            first_request = not bool(self._got_first_request["setup_server"])
            if first_request:
                # Trigger callback generation for embedded layouts.
                if self.blueprint._layout_is_function:
                    _ = self.blueprint.layout()
                self.register_callbacks()
            # Proceed as normally.
            super()._setup_server()
            if first_request:
                # Remap callback bindings to enable callback registration via the 'before_first_request' hook.
                self.callback = super().callback
                self.clientside_callback = super().clientside_callback
                # Set session secret. Used by some subclasses.
                if not self.server.secret_key:
                    self.server.secret_key = secrets.token_urlsafe(16)

    def hijack(self, app: dash.Dash):
        """
        Hijack another app. Typically, used with Dataiku 10 where the Dash object is instantiated outside user code.
        """
        # Change properties.
        readonly_props = app.config.__dict__.get("_read_only", {})
        app.config.update({k: v for k, v in self.config.items() if k not in readonly_props})
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


class StatefulDashTransform(DashTransform):

    def __init__(self):
        super().__init__()
        self.blueprint = DashBlueprint()
        self.components = []


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


class BlockingCallbackTransform(StatefulDashTransform):
    def __init__(self, timeout=60):
        super().__init__()
        self.timeout = timeout

    def transform_layout(self, layout):
        children = _as_list(layout.children) + self.components
        layout.children = children

    def apply(self, callbacks, clientside_callbacks):
        callbacks = self.apply_serverside(callbacks)
        return callbacks, clientside_callbacks + self.blueprint.clientside_callbacks

    def apply_serverside(self, callbacks):
        for callback in callbacks:
            if not callback.kwargs.get("blocking", None):
                continue

            timeout = callback.kwargs.get("blocking_timeout", self.timeout)
            callback_id = callback.uid
            # Bind proxy components.
            start_client_id = f"{callback_id}_start_client"
            start_client_ctx = f"{callback_id}_start_client_ctx"
            end_server_id = f"{callback_id}_end_server"
            end_client_id = f"{callback_id}_end_client"
            start_blocked_id = f"{callback_id}_start_blocked"
            end_blocked_id = f"{callback_id}_end_blocked"
            self.components.extend([
                dcc.Store(id=start_client_id),
                dcc.Store(id=end_server_id),
                dcc.Store(id=end_client_id),
                dcc.Store(id=start_blocked_id),
                dcc.Store(id=start_client_ctx),
                CycleBreaker(id=end_blocked_id)
            ])
            # Bind start signal callback.
            start_callback = f"""function()
            {{
                const start = arguments[arguments.length-3];
                const end = arguments[arguments.length-2];
                let ctx = arguments[arguments.length-1];
                const now = new Date().getTime();
                const trigger = dash_clientside.callback_context.triggered[0];
                const no = window.dash_clientside.no_update  
                // Update context.
                if(trigger !== undefined){{
                    if(!trigger.prop_id.startsWith('{end_blocked_id}')){{
                        ctx = {{}}
                        keys = ["inputs", "inputs_list", "triggered"];
                        for (let i = 0; i < keys.length; i++) {{
                            let key = keys[i];
                            ctx[key] = dash_clientside.callback_context[key];
                        }}                        
                    }}
                }}
                // First run => INVOKE.
                if(!end & !start){{
                    return [now, null, ctx];
                }}
                // Timeout reached  => INVOKE (but don't refresh context).
                if((now - start)/1000 > {timeout}){{
                    return [now, null, ctx];
                }}
                // Not completed first time => BLOCK.
                if(!end){{
                    return [no, now, no];
                }}
                // Previous invoke ended => INVOKE (but don't update context).
                if(end > start){{
                    return [now, null, ctx];
                }}
                // Callback running.
                return [no, now, no];
            }}"""
            self.blueprint.clientside_callback(
                start_callback,
                [Output(start_client_id, "data"), Output(start_blocked_id, "data"), Output(start_client_ctx, "data")],
                [Input(end_blocked_id, "dst")] + list(callback.inputs),
                [State(start_client_id, "data"), State(end_client_id, "data"), State(start_client_ctx, "data")],
            )
            # Bind end signal callback.
            end_callback = """function(endServerId, startBlockedId)
            {
                const now = new Date().getTime();
                if(startBlockedId){
                    return [now, now];
                }
                return [now, window.dash_clientside.no_update];
            }"""
            self.blueprint.clientside_callback(
                end_callback,
                [Output(end_client_id, "data"), Output(end_blocked_id, "src")],
                Input(end_server_id, "data"),
                State(start_blocked_id, "data")
            )
            # Modify the original callback to send finished signal.
            num_outputs = len(callback.outputs)
            out_flex_key = callback.outputs.append(Output(end_server_id, "data"))
            # Change original inputs to state.
            for i, item in enumerate(callback.inputs):
                callback.inputs[i] = State(item.component_id, item.component_property)
            # Add new input trigger.
            in_flex_key = callback.inputs.append(Input(start_client_id, "data"))
            st_flex_key = callback.inputs.append(State(start_client_ctx, "data"))
            # Modify the callback function accordingly.
            f = callback.f
            callback.f = skip_input_signal_add_output_signal(num_outputs, out_flex_key, in_flex_key, st_flex_key)(f)

        return callbacks


def skip_input_signal_add_output_signal(num_outputs, out_flex_key, in_flex_key, st_flex_key):
    def wrapper(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            args, kwargs, fltr = _skip_inputs(args, kwargs, [in_flex_key, st_flex_key])
            cached_ctx = fltr[1]
            single_output = num_outputs <= 1
            if cached_ctx is not None and "triggered" in cached_ctx:
                ctx = context_value.get()
                ctx["triggered_inputs"] = cached_ctx["triggered"]
                context_value.set(ctx)
            try:
                outputs = f(*args, **kwargs)
            except Exception:
                logging.exception(f"Exception raised in blocking callback [{f.__name__}]")
                outputs = no_update if single_output else [no_update] * num_outputs       
            
            return _append_output(outputs, datetime.utcnow().timestamp(), single_output, out_flex_key)

        return decorated_function

    return wrapper


# endregion

# region Log transform


class LogConfig:
    def __init__(self, log_output, log_writer_map: Dict[int, Callable],
                 layout_transform: Callable[[List[Component]], List[Component]]):
        self.log_output = log_output
        self.log_writer_map = log_writer_map
        self.layout_transform = layout_transform


def setup_notifications_log_config():
    log_id = "notifications_provider"
    log_output = Output(log_id, "children", allow_duplicate=True)

    def notification_layout_transform(layout: List[Component]):
        import dash_mantine_components as dmc

        layout.append(html.Div(id=log_id))
        return [dmc.NotificationProvider(layout)]

    return LogConfig(log_output, get_notification_log_writers(), notification_layout_transform)


def setup_div_log_config():
    log_id = "log"

    def div_layout_transform(layout: List[Component]):
        layout.append(html.Div(id=log_id))
        return layout

    log_output = Output(log_id, "children", allow_duplicate=True)
    return LogConfig(log_output, get_default_log_writers(), div_layout_transform)


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
    def __init__(self, log_config=None, try_use_mantine=True):
        super().__init__()
        # Per default, try to use dmc notification system.
        if log_config is None and try_use_mantine:
            try:
                log_config = setup_notifications_log_config()
            except ImportError:
                msg = "Failed to import dash-mantine-components, falling back to simple div for log output."
                logging.warning(msg)
        # Otherwise, use simple div.
        if log_config is None:
            log_config = setup_div_log_config()
        # Bind the resulting log config.
        self.log_config = log_config

    def transform_layout(self, layout):
        layout.children = self.log_config.layout_transform(_as_list(layout.children))

    def apply(self, callbacks, clientside_callbacks):
        callbacks = self.apply_serverside(callbacks)
        return callbacks, clientside_callbacks

    def apply_serverside(self, callbacks):
        for callback in callbacks:
            if not callback.kwargs.get("log", None):
                continue
            # Add the log component as output.
            single_output = len(callback.outputs) <= 1
            out_flex_key = callback.outputs.append(self.log_config.log_output)
            # Modify the callback function accordingly.
            f = callback.f
            logger = DashLogger(self.log_config.log_writer_map)  # TODO: What about scope?
            callback.f = bind_logger(logger, single_output, out_flex_key)(f)

        return callbacks

    def get_dependent_transforms(self):
        return [MultiplexerTransform()]


def bind_logger(logger, single_output, out_flex_key):
    def wrapper(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            logger.clear()
            outputs = f(*args, **kwargs, dash_logger=logger)
            return _append_output(outputs, logger.get_output(), single_output, out_flex_key)

        return decorated_function

    return wrapper


# endregion

# region Cycle breaker transform

class CycleBreakerTransform(StatefulDashTransform):

    def __init__(self):
        super().__init__()

    def transform_layout(self, layout):
        children = _as_list(layout.children) + self.components
        layout.children = children

    def apply(self, callbacks, clientside_callbacks):
        cycle_inputs = {}
        # Update inputs.
        for c in callbacks + clientside_callbacks:
            for i in c.inputs:
                if isinstance(i, CycleBreakerInput):
                    cid = self._cycle_break_id(i)
                    cycle_inputs[cid] = (i.component_id, i.component_property)
                    i.component_id = cid
                    i.component_property = "dst"
        # Construct components.
        self.components = [CycleBreaker(id=cid) for cid in cycle_inputs]
        # Construct callbacks.
        f = "function(x){return x;}"
        cycle_callbacks = []
        for cid in cycle_inputs:
            cb = CallbackBlueprint(Output(cid, "src"), Input(*cycle_inputs[cid]))
            cb.f = f
            cycle_callbacks.append(cb)
        return callbacks, clientside_callbacks + cycle_callbacks

    @staticmethod
    def _cycle_break_id(d: DashDependency):
        return f"{str(d).replace('.', '_')}_breaker"


class CycleBreakerInput(Input):
    def __init__(self, component_id, component_property):
        super().__init__(component_id, component_property)


# endregion

# region Global blueprint object (to emulate Dash 2.0 import syntax)

GLOBAL_BLUEPRINT = DashBlueprint()


def callback(*args, **kwargs):
    return GLOBAL_BLUEPRINT.callback(*args, **kwargs)


def clientside_callback(clientside_function, *args, **kwargs):
    return GLOBAL_BLUEPRINT.clientside_callback(clientside_function, *args, **kwargs)


# TODO: Include or not? The plugin still seems a bit immature.
def register(blueprint: DashBlueprint, name: str, prefix=None, **kwargs):
    if prefix is not None:
        prefix_transform = PrefixIdTransform(prefix)
        blueprint.transforms.append(prefix_transform)
    blueprint.register_callbacks(GLOBAL_BLUEPRINT)
    dash.register_page(name, layout=blueprint._layout_value, **kwargs)


# endregion

# region Prefix ID transform


class PrefixIdTransform(DashTransform):
    def __init__(self, prefix, prefix_func=None, escape=None):
        """
        The PrefixIdTransform adds a prefix to all component ids of the DashBlueprint, including 
        their references in callbacks. It is typically used to avoid ID collisions between 
        blueprints when they are registered on or embedded in the main Dash application.

        Args:
            prefix (str): The prefix that will be added to the component_ids.
            prefix_func (callable(str, Component, callable(str)): A function used to modify
                the ID of the components. This function must accept three arguments: the 
                prefix string, a Dash component, and the escape function. If not provided,
                the `prefix_component()` function is used, which relies on `apply_prefix()` 
                to calculate the new ID.
            escape (callable(str)): A function that will be called by `apply_prefix()` to 
                determine whether the component's ID should remain unaltered (escaped). The
                function should accept a string (the component_id) and return a boolean. 
                By default, `default_prefix_escape()` is used, which avoids modifying 
                certain IDs that start with "a-" or "anchor-".

        Note: `PrefixIdTransform` is automatically registered as `transforms` by 
               the `DashBlueprint.register()` method when the `prefix` parameter is specified.
        """
        super().__init__()
        self.prefix = prefix
        self.prefix_func = prefix_func if prefix_func is not None else prefix_component
        self.escape = default_prefix_escape if escape is None else escape

    def _apply(self, callbacks):
        for callback in callbacks:
            for i in callback.inputs:
                i.component_id = apply_prefix(self.prefix, i.component_id, self.escape)
            for o in callback.outputs:
                o.component_id = apply_prefix(self.prefix, o.component_id, self.escape)
        return callbacks

    def apply_serverside(self, callbacks):
        return self._apply(callbacks)

    def apply_clientside(self, callbacks):
        return self._apply(callbacks)

    def transform_layout(self, layout):
        prefix_recursively(layout, self.prefix, self.prefix_func, self.escape)


def default_prefix_escape(component_id: str):
    if isinstance(component_id, str):
        if component_id.startswith("a-"):  # intended usage is for anchors
            return True
        if component_id.startswith("anchor-"):  # intended usage is for anchors
            return True
    return False


def apply_prefix(prefix, component_id, escape):
    if escape(component_id):
        return component_id
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


def prefix_recursively(item, key, prefix_func, escape):
    prefix_func(key, item, escape)
    if hasattr(item, "children"):
        children = _as_list(item.children)
        for child in children:
            prefix_recursively(child, key, prefix_func, escape)


def prefix_component(key: str, component: Component, escape: Callable):
    if hasattr(component, "id"):
        component.id = apply_prefix(key, component.id, escape)
    if not hasattr(component, "_namespace"):
        return
    # Special handling of dash bootstrap components. TODO: Maybe add others?
    if component._namespace == "dash_bootstrap_components":
        if component._type == "Tooltip":
            component.target = apply_prefix(key, component.target, escape)


# TODO: Test this one.
def dynamic_prefix(app: Union[DashBlueprint, DashProxy], component: Component):
    bp: DashBlueprint = app if isinstance(app, DashBlueprint) else app.blueprint
    prefix_transforms = list(filter(lambda t: isinstance(t, PrefixIdTransform), bp.transforms))
    # No transform, just return.
    if len(prefix_transforms) == 0:
        return
    prefix_transform: PrefixIdTransform = prefix_transforms[0]
    prefix_recursively(component, prefix_transform.prefix, prefix_transform.prefix_func, prefix_transform.escape)


# endregion

# region Trigger transform (the only default transform)


class Trigger(Input):
    """
    Like an Input, a trigger can trigger a callback, but it's values it not included in the resulting function call.
    """

    def __init__(self, component_id, component_property):
        super().__init__(component_id, component_property)


class TriggerTransform(DashTransform):

    def apply_serverside(self, callbacks):
        for callback in callbacks:
            is_trigger = [isinstance(item, Trigger) for item in callback.inputs]
            # Check if any triggers are there.
            if not any(is_trigger):
                continue
            # If so, filter the callback args.
            f = callback.f
            callback.f = filter_args(is_trigger)(f)
        return callbacks

    def apply_clientside(self, callbacks):
        for callback in callbacks:
            is_not_trigger = [not isinstance(item, Trigger) for item in callback.inputs]
            # Check if any triggers are there.
            if all(is_not_trigger):
                continue
            # If so, filter the callback args.
            args = [f"arg{i}" for i in range(len(callback.inputs))]
            filtered_args = compress(args, is_not_trigger)
            if isinstance(callback.f, ClientsideFunction):
                callback.f = f"window.dash_clientside['{callback.f.namespace}']['{callback.f.function_name}']"
            callback.f = f"""
function({", ".join(args)}) {{
const func = {callback.f};
return func({", ".join(filtered_args)});
}}"""
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

class MultiplexerTransform(DashTransform):
    """
    The MultiplexerTransform was previously used to make it possible to target an output by multiple callbacks, but as
    per Dash 2.9 this function is now included, but by default disabled. To achieve similar behaviour as before (and
    thus improve backwards compatibility), the MultiplexerTransform enables the functionality automagically.
    """

    def __init__(self):
        super().__init__()

    def apply(self, callbacks, clientside_callbacks):
        all_callbacks = callbacks + clientside_callbacks
        # Group by output.
        output_map = defaultdict(list)
        for callback in all_callbacks:
            for output in callback.outputs:
                output_map[_output_id_without_wildcards(output)].append(output)
        # Set allow_duplicate where needed.
        for output_id in output_map:
            # If there is only one output, multiplexing is not needed.
            if len(output_map[output_id]) == 1:
                continue
            for entry in output_map[output_id]:
                entry.allow_duplicate = True

        return callbacks, clientside_callbacks


def _output_id_without_wildcards(output: Output) -> str:
    i, p = output.component_id, output.component_property
    if isinstance(i, dict):
        i = json.dumps({k: i[k] for k in sorted(i) if i[k] not in [ALL, MATCH, ALLSMALLER]})
    return f"{i}_{p}"


# endregion

# region SerializationTransform

class SerializationTransform(DashTransform):

    def apply_serverside(self, callbacks):
        for callback in callbacks:
            f = callback.f
            callback.f = self._unpack_pack_callback(callback)(f)
        return callbacks

    def _try_load(self, data: Any, ann=None):
        raise NotImplementedError

    def _try_dump(self, obj: Any):
        raise NotImplementedError

    def _unpack_pack_callback(self, callback):
        full_arg_spec = inspect.getfullargspec(callback.f)

        def unpack_pack_args(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                args = list(args)
                # Replace args and kwargs. # TODO: Is recursion needed?
                for i, arg in enumerate(args):
                    an = full_arg_spec.annotations.get(full_arg_spec.args[i])
                    value = [self._try_load(a, an) for a in arg] if isinstance(arg, list) else self._try_load(arg, an)
                    args[i] = value
                for key in kwargs:
                    arg = kwargs[key]
                    an = full_arg_spec.annotations.get(key)
                    value = [self._try_load(a, an) for a in arg] if isinstance(arg, list) else self._try_load(arg, an)
                    kwargs[key] = value
                # Evaluate function.
                data = f(*args, **kwargs)
                # Capture outputs.
                data = self._try_dump(data)
                if isinstance(data, list):
                    data = [self._try_dump(element) for element in data]
                if isinstance(data, tuple):
                    data = tuple([self._try_dump(element) for element in data])
                if isinstance(data, dict):
                    data = {key: self._try_dump(data[key]) for key in data}
                return data

            return decorated_function

        return unpack_pack_args

    def sort_key(self):
        return 0

# endregion

# region DataclassTransform

class DataclassTransform(SerializationTransform):

    def _try_load(self, data: Any, ann=None) -> Any:
        if not dataclasses.is_dataclass(ann):
            return data
        return fromdict(ann, data)

    def _try_dump(self, obj: Any) -> Any:
        if not dataclasses.is_dataclass(obj):
            return obj
        return asdict(obj)


# endregion

# region Server side output transform


class ServersideBackend:
    def get(self, key, ignore_expired=False):
        raise NotImplementedError()

    def set(self, key, value):
        raise NotImplementedError()

    def has(self, key):
        raise NotImplementedError()

    @property
    def uid(self) -> str:
        """
        Backend identifier. Must be unique across the backend registry. Defaults to class name.
        """
        return self.__class__.__name__


class FileSystemBackend(FileSystemCache, ServersideBackend):
    def __init__(self, cache_dir="file_system_backend", **kwargs):
        super().__init__(cache_dir, **kwargs)

    def get(self, key: str, ignore_expired=False):
        if key is None:
            return None
        if not ignore_expired:
            return super().get(key)
        # TODO: This part must be implemented for each type of cache.
        filename = self._get_filename(key)
        try:
            with self._safe_stream_open(filename, "rb") as f:
                _ = struct.unpack("I", f.read(4))[0]
                return self.serializer.load(f)
        except FileNotFoundError:
            pass
        except (OSError, EOFError, struct.error):
            logging.warning(
                "Exception raised while handling cache file '%s'",
                filename,
                exc_info=True,
            )
        return None

    @property
    def uid(self) -> str:
        """
        Backend identifier. Must be unique across the backend registry.
        """
        return f"{self.__class__.__name__}:{self._path}"


class RedisBackend(RedisCache, ServersideBackend):
    """
    Store that uses Redis as backend. Note, that the timeout must be large enough that a (k,v) pair NEVER expires
    during a user session. If it does, the user experience for those sessions will be degraded.
    """

    def __init__(self, default_timeout=24 * 3600, **kwargs):
        super().__init__(default_timeout=default_timeout, **kwargs)

    def get(self, key, ignore_expired=False):
        # TODO: Is there any way to honor ignore_expired for redis? I don't think so
        return super().get(key)


class EnrichedOutput(Output):
    """
    Like a normal Output, includes additional properties related to storing the data.
    """

    def __init__(self, component_id, component_property, allow_duplicate=False, backend=None, session_check=None,
                 arg_check=True):
        super().__init__(component_id, component_property, allow_duplicate)
        self.backend = backend
        self.session_check = session_check
        self.arg_check = arg_check


class ServersideOutputTransform(SerializationTransform):
    prefix: str = "SERVERSIDE_"

    def __init__(self,
                 backends: Optional[List[ServersideBackend]] = None,
                 default_backend: Optional[ServersideBackend] = None):
        super().__init__()
        # Per default, use file system backend.
        if backends is None:
            backends = [FileSystemBackend()]
        self._default_backend: ServersideBackend = backends[0] if default_backend is None else default_backend
        # Setup registry for easy/fast access.
        self._backend_registry: Dict[str, ServersideBackend] = {backend.uid: backend for backend in backends}

    def _try_load(self, data: Any, ann=None) -> Any:
        if not isinstance(data, str):
            return data
        if not data.startswith(self.prefix):
            return data
        obj = json.loads(data[len(self.prefix):])
        backend = self._backend_registry[obj["backend_uid"]]
        value = backend.get(obj["key"], ignore_expired=True)
        return value

    def _try_dump(self, obj: Any) -> Any:
        if not isinstance(obj, Serverside):
            return obj
        backend_uid = obj.backend_uid
        # If not backend it set, use the default.
        if backend_uid is None:
            backend_uid = self._default_backend.uid
        # Dump the data.
        backend = self._backend_registry[backend_uid]
        backend.set(obj.key, obj.value)
        # Return lookup structure.
        data = dict(backend_uid=backend_uid, key=obj.key)
        return f"{self.prefix}{json.dumps(data)}"


class Serverside(Generic[T]):

    def __init__(self, value: T, key: str = None, backend: Union[ServersideBackend, str, None] = None):
        self.value = value
        self.key: str = str(uuid.uuid4()) if key is None else key
        self.backend_uid: str = backend.uid if isinstance(backend, ServersideBackend) else backend


# endregion

# region No output transform


class NoOutputTransform(StatefulDashTransform):
    def __init__(self):
        super().__init__()

    def transform_layout(self, layout):
        children = _as_list(layout.children) + self.components
        layout.children = children

    def _apply(self, callbacks):
        for callback in callbacks:
            if len(callback.outputs) == 0:
                output_id = callback.uid
                hidden_div = html.Div(id=output_id, style={"display": "none"})
                callback.outputs.append(Output(output_id, "children"))
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
    def __init__(self, *args, **kwargs):
        transforms = [
            TriggerTransform(),
            LogTransform(),
            MultiplexerTransform(),
            NoOutputTransform(),
            CycleBreakerTransform(),
            BlockingCallbackTransform(),
            ServersideOutputTransform(),
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


def _skip_inputs(args, kwargs, keys: List[Any]):
    fltr = []
    str_keys = [key for key in keys if isinstance(key, str)]
    int_keys = [key for key in keys if isinstance(key, int)]
    # Drop str keys.
    for key in str_keys:
        fltr.append(kwargs.pop(key))
    # Filter the other ones.
    if any(int_keys):
        args = list(args)
        fltr.extend([arg for i, arg in enumerate(args) if i in keys])
        args = [arg for i, arg in enumerate(args) if i not in keys]
    # TODO: Do we need to handle None?
    return args, kwargs, fltr


def _append_output(outputs, value, single_output, out_idx):
    # Handle flex signature.
    if isinstance(outputs, dict):
        outputs[out_idx] = value
        return outputs
    # Handle single output.
    if single_output:
        return [outputs, value]
    # Finally, the "normal" case.
    return _as_list(outputs) + [value]


def _create_callback_id(item):
    cid = item.component_id
    if isinstance(cid, dict):
        cid = {key: cid[key] for key in cid if cid[key] not in _wildcard_mappings}
        cid = json.dumps(cid)
    return "{}.{}".format(cid, item.component_property)


def _check_multi(item):
    cid = item.component_id
    if not isinstance(cid, dict):
        return False
    vs = cid.values()
    return ALL in vs or ALLSMALLER in vs


def plotly_jsonify(data):
    return json.loads(json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder))

# endregion
