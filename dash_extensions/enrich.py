from __future__ import annotations

import functools
import hashlib
import json
import logging
import secrets
import struct
import sys
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
from more_itertools import flatten
from collections import defaultdict
from typing import Dict, Callable, List, Union, Any, Tuple, Optional
from datetime import datetime
from dash_extensions import CycleBreaker

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
    def register(self, app: Union[dash.Dash, DashProxy], module, prefix=None, **kwargs):
        if prefix is not None:
            prefix_transform = PrefixIdTransform(prefix)
            self.transforms.append(prefix_transform)
        self.register_callbacks(app)
        dash.register_page(module, layout=self._layout_value, **kwargs)

    def clear(self):
        self.callbacks = []
        self.clientside_callbacks = []
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
    """
    DashProxy is a wrapper around the DashBlueprint object enabling drop-in replacement of the original Dash object. It
    enables transforms (via the DashBlueprint object), performs the necessary app configuration for all transforms to
    work (e.g. setting a secret key on the server), and exposes convenience functions such as 'hijack'.
    """

    def __init__(self, *args, transforms=None, include_global_callbacks=True, blueprint=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.blueprint = DashBlueprint(transforms,
                                       include_global_callbacks=include_global_callbacks) if blueprint is None else blueprint

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
        first_request = not bool(self._got_first_request["setup_server"])
        if first_request:
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
            single_output = len(callback.outputs) <= 1
            out_flex_key = callback.outputs.append(Output(end_server_id, "data"))
            # Change original inputs to state.
            for i, item in enumerate(callback.inputs):
                callback.inputs[i] = State(item.component_id, item.component_property)
            # Add new input trigger.
            in_flex_key = callback.inputs.append(Input(start_client_id, "data"))
            st_flex_key = callback.inputs.append(State(start_client_ctx, "data"))
            # Modify the callback function accordingly.
            f = callback.f
            callback.f = skip_input_signal_add_output_signal(single_output, out_flex_key, in_flex_key, st_flex_key)(f)

        return callbacks


def skip_input_signal_add_output_signal(single_output, out_flex_key, in_flex_key, st_flex_key):
    def wrapper(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            args, kwargs, fltr = _skip_inputs(args, kwargs, [in_flex_key, st_flex_key])
            cached_ctx = fltr[1]
            if cached_ctx is not None and "triggered" in cached_ctx:
                ctx = context_value.get()
                ctx["triggered_inputs"] = cached_ctx["triggered"]
                context_value.set(ctx)
            outputs = f(*args, **kwargs)
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
    log_output = Output(log_id, "children")

    def notification_layout_transform(layout: List[Component]):
        import dash_mantine_components as dmc

        layout.append(html.Div(id=log_id))
        return [dmc.NotificationsProvider(layout)]

    return LogConfig(log_output, get_notification_log_writers(), notification_layout_transform)


def setup_div_log_config():
    log_id = "log"

    def div_layout_transform(layout: List[Component]):
        layout.append(html.Div(id=log_id))
        return layout

    log_output = Output(log_id, "children")
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

class CycleBreakerTransform(DashTransform):

    def __init__(self):
        super().__init__()
        self.components = []

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
    prefix_component(prefix_transform.prefix, component, prefix_transform.escape)


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
            is_trigger = [isinstance(item, Trigger) for item in callback.inputs]
            # Check if any triggers are there.
            if not any(is_trigger):
                continue
            # If so, filter the callback args.
            f = callback.f
            callback.f = filter_args(is_trigger)(f)
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
            for output in callback.outputs:
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
        max_priority = -1
        idx_priority = -1
        for i, callback in enumerate(callbacks):
            mp_id = _mp_id(output, i)
            mp_id_escaped = _escape_wildcards(mp_id)
            # Create proxy element.
            proxies.append(_mp_element(mp_id_escaped.copy()))
            # Assign proxy element as output.
            callback.outputs[callback.outputs.index(output)] = Output(mp_id_escaped.copy(), _mp_prop())
            # Create proxy input.
            inputs.append(Input(mp_id, _mp_prop()))
            # Figure out which is the highest priority.
            p = callback.kwargs.get("priority", 0)
            if p > max_priority:
                max_priority = p
                idx_priority = i
        # Collect proxy elements to add to layout.
        self.proxy_map[output].extend(proxies)
        # Create multiplexer callback. Clientside for best performance. TODO: Is this robust?
        self.blueprint.clientside_callback(
            f"""
            function(){{
                const ts = dash_clientside.callback_context.triggered;
                for (let i = 0; i < ts.length; i++) {{
                    idx = JSON.parse(ts[i].prop_id.split('.')[0]).idx;
                    if(idx === {idx_priority}){{
                        return ts[i].value;
                    }}
                }}
                return ts[0].value;
            }}
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

    # NOTE: Doesn't make sense for clientside callbacks.

    def _get_attr_with_default(self, output, attr):
        if hasattr(output, attr):
            value = getattr(output, attr)
            if value is not None:
                return value
        return getattr(self, attr)

    def apply_serverside(self, callbacks):
        # 1) Create index.
        serverside_callbacks = []
        serverside_output_map = {}
        for callback in callbacks:
            # If memoize keyword is used, serverside caching is needed.
            memoize = callback.kwargs.get("memoize", None)
            serverside = False
            # Keep tract of which outputs are server side outputs.
            for output in callback.outputs:
                if isinstance(output, ServersideOutput):
                    serverside_output_map[_create_callback_id(output)] = output
                    serverside = True
                # Set default values.
                if not isinstance(output, ServersideOutput) and not memoize:
                    continue
                output.backend = self._get_attr_with_default(output, "backend")
                output.arg_check = self._get_attr_with_default(output, "arg_check")
                output.session_check = self._get_attr_with_default(output, "session_check")
            # Keep track of server side callbacks.
            if serverside or memoize:
                serverside_callbacks.append(callback)
        # 2) Inject cached data into callbacks.
        for callback in callbacks:
            # Figure out which args need loading.
            items = callback.inputs
            item_ids = [_create_callback_id(item) for item in items]
            serverside_outputs = [serverside_output_map.get(item_id, None) for item_id in item_ids]
            # If any arguments are packed, unpack them.
            if any(serverside_outputs):
                f = callback.f
                callback.f = _unpack_outputs(serverside_outputs)(f)
        # 3) Apply the caching itself.
        for i, callback in enumerate(serverside_callbacks):
            f = callback.f
            callback.f = _pack_outputs(callback)(f)
        # 4) Strip special args.
        for callback in callbacks:
            for key in ["memoize"]:
                callback.kwargs.pop(key, None)

        return callbacks


def _unpack_outputs(serverside_outputs):
    def unpack(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not any(serverside_outputs):
                return f(*args, **kwargs)
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
            return f(*args, **kwargs)

        return decorated_function

    return unpack


def _pack_outputs(callback):
    memoize = callback.kwargs.get("memoize", None)

    def packed_callback(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            multi_output = callback.multi_output
            # If memoize is enabled, we check if the cache already has a valid value.
            if memoize:
                # Figure out if an update is necessary.
                unique_ids = []
                update_needed = False
                for i, output in enumerate(callback.outputs):
                    # Filter out Triggers (a little ugly to do here, should ideally be handled elsewhere).
                    to_skip = [isinstance(item, Trigger) for item in callback.inputs]
                    filtered_args = [arg for i, arg in enumerate(args) if not to_skip[i]]
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
                        if isinstance(callback.outputs[i], ServersideOutput)
                        else callback.outputs[i].backend.get(uid)
                        for i, uid in enumerate(unique_ids)
                    ]
                    return results if multi_output else results[0]
            # Do the update.
            data = f(*args, **kwargs)
            data = list(data) if multi_output else [data]
            if callable(memoize):
                data = memoize(data)
            for i, output in enumerate(callback.outputs):
                # Skip no_update updates.
                if isinstance(data[i], type(no_update)):
                    continue
                # Replace only for server side outputs.
                serverside_output = isinstance(callback.outputs[i], ServersideOutput)
                if serverside_output or memoize:
                    # Filter out Triggers (a little ugly to do here, should ideally be handled elsewhere).
                    to_skip = [isinstance(item, (Trigger, DummyDependency)) for item in callback.inputs]
                    filtered_args = [arg for i, arg in enumerate(args) if not to_skip[i]]
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

# region [Magic] transform

class OperatorOutput(Output):
    """
    Like a normal Output, but enables list and dict manipulations.
    """


class Operator:
    def __init__(self, path: Optional[List] = None, operations: Optional[List] = None):
        self.path = path if path is not None else []
        self.operations = operations if operations is not None else []

    def __getitem__(self, key):
        return Operator(self.path + [key], operations=self.operations)

    def __setitem__(self, key, item):
        self.path += [key]
        return self.assign(item)

    def collect(self, opr, **kwargs):
        self.operations.append(dict(opr=opr, pth=self.path, **kwargs))
        self.path = []
        return self

    @property
    def list(self):
        return ListOperator(self)

    @property
    def dict(self):
        return DictOperator(self)

    def assign(self, item):
        return self.collect("assign", item=item)

    def apply(self):
        return self.operations


class ListOperator:
    def __init__(self, operator: Optional[Operator] = None):
        self.operator = operator

    def _collect(self, opr, **kwargs):
        return self.operator.collect(f"list_{opr}", **kwargs)

    def apply(self):
        return self.operator.apply()

    def append(self, item):
        return self._collect("append", item=item)

    def extend(self, iterable):
        return self._collect("extend", array=list(iterable))

    def insert(self, index, item):
        return self._collect("insert", item=item, index=index)

    def remove(self, item):
        # NB: Remove ALL occurances of item, not just the first one.
        return self._collect("remove", item=item)

    def pop(self, index):
        return self._collect("pop", index=index)

    def clear(self):
        return self._collect("clear")

    def sort(self):
        return self._collect("sort")

    def reverse(self):
        return self._collect("reverse")


class DictOperator:
    def __init__(self, operator: Optional[Operator] = None):
        self.operator = operator

    def _collect(self, opr, **kwargs):
        return self.operator.collect(f"dict_{opr}", **kwargs)

    def apply(self):
        return self.operator.apply()

    def set(self, key, item):
        return self._collect("set", key=key, item=item)

    def pop(self, key):
        return self._collect("pop", key=key)

    def update(self, obj):
        return self._collect("update", obj=obj)

    def clear(self):
        return self._collect("clear")


class OperatorTransform(DashTransform):
    def __init__(self):
        super().__init__()
        self.components = []
        self.operator_outputs = []
        self.blueprint = DashBlueprint()

    def transform_layout(self, layout):
        children = _as_list(layout.children) + self.components
        layout.children = children

    def _apply(self, callback, output):
        original_id = str(output).replace(".", "_")  # .component_id
        relay_id = _relay_id(original_id)
        if str(output) not in self.operator_outputs:
            # Append new relay component.
            relay_component = dcc.Store(id=relay_id)
            self.components.append(relay_component)
            # Add clientside callback to perform modifications.
            self.blueprint.clientside_callback(f"""function(operations, current){{
                // Handle empty init call.
                if (typeof operations === 'undefined'){{
                    return window.dash_clientside.no_update;
                }}
                // Map non-list actions to list to enable iteration.
                if (!(Array.isArray(operations))){{
                    operations = [operations];
                }}
                // Function for resolving sub elements.
                const drill = (obj, pth, lvl=0) => {{
                    if(lvl === pth.length){{return obj;}}
                    return drill(obj[pth[lvl]], pth, lvl+1);
                }}
                // Wrap current in list to enable index access.
                lst = [current];
                // Action.
                for (const x of operations) {{
                    let pth = [0].concat(x.pth);
                    let idx = pth[pth.length - 1];
                    let obj = drill(lst, pth.slice(0,-1));
                    switch(x.opr) {{
                      case "assign":
                        obj[idx] = x.item;             
                        break;
                      // List action(s).
                      case "list_append":
                        obj[idx].push(x.item)
                        break;
                      case "list_extend":
                        obj[idx] = obj[idx].concat(x.array);
                        break;
                      case "list_insert":
                        obj[idx].splice(x.index, 0, x.item);
                        break;
                      case "list_remove":
                        obj[idx] = obj[idx].filter(function(ele){{
                            return ele != x.item;
                        }});
                        break;
                      case "list_pop":
                        obj[idx].splice(x.index, 1);
                        break;
                      case "list_reverse":
                        obj[idx].reverse();
                        break;
                      case "list_sort":
                        // TODO: Make it possible to inject sorting function
                        obj[idx].sort();
                        break;
                      case "list_clear":
                        obj[idx] = []             
                        break;
                      // Dict action(s).
                      case "dict_set":
                        obj[idx][x.key] = x.item;
                        break;
                      case "dict_pop":
                        delete obj[idx][x.key];
                        break;
                      case "dict_clear":
                        obj[idx] = {{}};             
                        break;
                      case "dict_update":
                        obj[idx] = {{
                            ...obj[idx],
                            ...x.obj
                        }};
                      // Unknown action(s).
                      default:
                        console.log("Received unknown action for component {original_id}.");
                        console.log(x);
                        console.log("Update will be skipped.");
                    }}
                }}
                // Make sure out ref != input ref (otherwise, React can get confused)
                const result = lst[0];
                if(Array.isArray(result)){{
                    return Array.from(result)
                }}
                if(typeof result === 'object'){{
                    return Object.assign({{}}, result);
                }}
                return result;
            }}""", output, Input(relay_id, "data"), State(output.component_id, output.component_property))
            # Record binding.
            self.operator_outputs.append(str(output))
        # Modify callback in-place to route output to the relay.
        callback.outputs[callback.outputs.index(output)] = Output(relay_id, "data")
        # Run apply if needed.
        f = callback.f
        callback.f = apply_operator()(f)

    def apply_serverside(self, callbacks):
        for callback in callbacks:
            for output in callback.outputs:
                if isinstance(output, OperatorOutput):
                    self._apply(callback, output)
        return callbacks

    def apply_clientside(self, callbacks):
        return callbacks + self.blueprint.clientside_callbacks

    def get_dependent_transforms(self):
        return [MultiplexerTransform()]


def apply_operator():
    def wrapper(f):
        @functools.wraps(f)
        def decorated_function(*args):
            output = f(*args)
            if isinstance(output, Operator):
                return output.apply()
            if hasattr(output, "__len__"):
                output = [o.apply() if isinstance(o, Operator) else o for o in output]
            return output

        return decorated_function

    return wrapper


def _relay_id(uid):
    return f"{uid}_operator_relay"


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
            CycleBreakerTransform(),
            BlockingCallbackTransform(),
            ServersideOutputTransform(**output_defaults),
            OperatorTransform()
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
        cid = {key: cid[key] if cid[key] not in _wildcard_mappings else _wildcard_mappings[cid[key]] for key in cid}
        cid = json.dumps(cid)
    return "{}.{}".format(cid, item.component_property)


def plotly_jsonify(data):
    return json.loads(json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder))

# endregion
