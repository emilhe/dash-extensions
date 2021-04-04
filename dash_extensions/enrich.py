import functools
import hashlib
import json
import pickle
import secrets
import uuid
import dash_core_components as dcc
import dash
import dash_html_components as html
import dash.dependencies as dd
import plotly

from dash.dependencies import Input, State, Output, MATCH, ALL, ALLSMALLER, _Wildcard
from dash.development.base_component import Component
from flask import session
from flask_caching.backends import FileSystemCache
from more_itertools import flatten
from collections import defaultdict
from typing import Dict

_wildcard_mappings = {ALL: "<ALL>", MATCH: "<MATCH>", ALLSMALLER: "<ALLSMALLER>"}
_wildcard_values = list(_wildcard_mappings.values())


# region Dash proxy


class DashProxy(dash.Dash):

    def __init__(self, *args, transforms=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.callbacks = []
        self.clientside_callbacks = []
        self.arg_types = [dd.Output, dd.Input, dd.State]
        self.transforms = transforms if transforms is not None else []
        # Do the transform initialization.
        for transform in self.transforms:
            transform.init(self)

    def callback(self, *args, **kwargs):
        """
         This method saves the callbacks on the DashTransformer object. It acts as a proxy for the Dash app callback.
        """
        # Parse Output/Input/State (could be made simpler by enforcing input structure)
        keys = ['output', 'inputs', 'state']
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
                        if not multi_output and isinstance(element, dd.Output):
                            component_id = element.component_id
                            if isinstance(component_id, dict):
                                multi_output = any([component_id[k] in [dd.ALLSMALLER, dd.ALL] for k in component_id])
                        callback[key].append(element)
                        arg_order.append(element)
        if not multi_output:
            multi_output = len(callback[dd.Output]) > 1
        # Save the kwargs for later.
        callback["kwargs"] = kwargs
        callback["sorted_args"] = arg_order
        callback["multi_output"] = multi_output
        # Save the callback for later.
        self.callbacks.append(callback)

        def wrapper(f):
            callback["f"] = f

        return wrapper

    def clientside_callback(self, clientside_function, *args, **kwargs):
        self.clientside_callbacks.append(dict(clientside_function=clientside_function, args=args, kwargs=kwargs))

    def _register_callbacks(self, app=None):
        callbacks = list(self._resolve_callbacks())
        app = super() if app is None else app
        for callback in callbacks:
            outputs = callback[dd.Output][0] if len(callback[dd.Output]) == 1 else callback[dd.Output]
            app.callback(outputs, callback[dd.Input], callback[dd.State], **callback["kwargs"])(callback["f"])

    def _register_clientside_callbacks(self, app=None):
        clientside_callbacks = list(self._resolve_clientside_callbacks())
        app = super() if app is None else app
        for callback in clientside_callbacks:
            app.clientside_callback(callback["clientside_function"], *callback["args"], **callback["kwargs"])

    def _register_all_callbacks(self, app=None):
        self._register_callbacks(app=app)
        self._register_clientside_callbacks(app=app)

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
        self._register_callbacks()
        self._register_clientside_callbacks()
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

    def _resolve_clientside_callbacks(self):
        """
         This method resolves the clientside_callbacks, i.e. it applies the clientside_callbacks injections.
        """
        clientside_callbacks = self.clientside_callbacks
        for transform in self.transforms:
            clientside_callbacks = transform.apply_clientside(clientside_callbacks)
        return clientside_callbacks

    def hijack(self, app: dash.Dash):
        # Change properties.
        app.config.update(self.config)
        app.title = self.title
        app.index_string = self.index_string
        # Inject layout.
        app.layout = html.Div()  # fool layout validator
        app._layout_value = self._layout_value
        # Register callbacks.
        self._register_callbacks(app)
        self._register_clientside_callbacks(app)
        # Setup secret.
        if not app.server.secret_key:
            app.server.secret_key = secrets.token_urlsafe(16)


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
    cid = item.component_id
    if isinstance(cid, dict):
        cid = {key: cid[key] if cid[key] not in _wildcard_mappings else _wildcard_mappings[cid[key]] for key in cid}
        cid = json.dumps(cid)
    return "{}.{}".format(cid, item.component_property)


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


def plotly_jsonify(data):
    return json.loads(json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder))


class DashTransform:

    def init(self, dt):
        pass

    def apply(self, callbacks):
        raise NotImplementedError()

    def apply_clientside(self, clientside_callbacks):
        return clientside_callbacks

    def layout(self, layout, layout_is_function):
        return layout


# endregion

# region Prefix ID transform

class PrefixIdTransform(DashTransform):

    def __init__(self, prefix):
        self.prefix = prefix
        self.initialized = False

    def apply(self, callbacks):
        for callback in callbacks:
            for arg in callback["sorted_args"]:
                arg.component_id = apply_prefix(self.prefix, arg.component_id)
        return callbacks

    def apply_clientside(self, callbacks):
        for callback in callbacks:
            for arg in callback["args"]:
                arg.component_id = apply_prefix(self.prefix, arg.component_id)
        return callbacks

    def layout(self, layout, layout_is_function):
        # TODO: Will this work with layout functions?
        if layout_is_function or not self.initialized:
            prefix_id_recursively(layout, self.prefix)
            self.initialized = True
        return layout


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


def prefix_id_recursively(item, key):
    if hasattr(item, "id"):
        item.id = apply_prefix(key, item.id)
    if hasattr(item, "children"):
        children = _as_list(item.children)
        for child in children:
            prefix_id_recursively(child, key)


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
            filtered_args = [arg for j, arg in enumerate(args) if not args_filter[j]]
            return f(*filtered_args)

        return decorated_function

    return wrapper


def trigger_filter(args):
    inputs_args = [item for item in args if isinstance(item, dd.Input) or isinstance(item, dd.State)]
    is_trigger = [isinstance(item, Trigger) for item in inputs_args]
    return is_trigger


# endregion

# region Multiplexer transform

def _mp_id(output: Output, idx: int) -> Dict[str, str]:
    return dict(id=output.component_id, prop=output.component_property, idx=idx)


def _mp_element(mp_id: Dict[str, str]) -> dcc.Store:
    return dcc.Store(id=mp_id)


def _mp_prop() -> str:
    return "data"


def inject_proxies(node, proxy_map):
    if not hasattr(node, "children") or node.children is None:
        return
    children = _as_list(node.children)
    modified = False
    for i, child in enumerate(children):
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


def inject_proxies_recursively(node, proxy_map):
    if not hasattr(node, "children") or node.children is None:
        return
    children = _as_list(node.children)
    modified = False
    for i, child in enumerate(children):
        # Do recursion.
        inject_proxies(child, proxy_map)
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

    def __init__(self, proxy_location="inplace"):
        self.initialized = False
        self.proxy_location = proxy_location
        self.proxy_map = defaultdict(lambda: [])
        self.app = DashProxy()

    def layout(self, layout, layout_is_function):
        if layout_is_function or not self.initialized:
            # Inject proxies in a user defined component.
            if self.proxy_location == "inplace":
                inject_proxies_recursively(layout, self.proxy_map)
            # Inject proxies in a component, either user defined or top level.
            else:
                target = self.proxy_location if isinstance(self.proxy_location, Component) else layout
                proxies = list(flatten(list(self.proxy_map.values())))
                target.children = _as_list(target.children) + proxies
            self.initialized = True
        return layout

    def apply(self, callbacks):
        # Group by output.
        output_map = defaultdict(list)
        for callback in callbacks:
            for output in callback[Output]:
                output_map[output].append(callback)
        # Apply multiplexer where needed.
        for output in output_map:
            # If there is only one output, multiplexing is not needed.
            if len(output_map[output]) == 1:
                continue
            self._apply_multiplexer(output, output_map[output])

        return callbacks

    def apply_clientside(self, clientside_callbacks):
        return clientside_callbacks + self.app.clientside_callbacks

    def _apply_multiplexer(self, output, callbacks):
        inputs = []
        proxies = []
        for i, callback in enumerate(callbacks):
            # Create proxy element.
            proxies.append(_mp_element(_mp_id(output, i)))
            # Assign proxy element as output.
            callback[Output][callback[Output].index(output)] = Output(proxies[-1].id, _mp_prop())
            # Create proxy input.
            inputs.append(Input(_mp_id(output, ALL), _mp_prop()))
        # Collect proxy elements to add to layout.
        self.proxy_map[output.component_id].extend(proxies)
        # Create multiplexer callback. Clientside for best performance. TODO: Is this robust?
        self.app.clientside_callback("""
            function(){
                return dash_clientside.callback_context.triggered[0].value;
            }
        """, output, inputs, prevent_initial_call=True)


# endregion

# region Server side output transform

class EnrichedOutput(Output):
    """
     Like a normal Output, includes additional properties related to storing the data.
    """

    def __init__(self, component_id, component_property, backend=None, session_check=None):
        super().__init__(component_id, component_property)
        self.backend = backend
        self.session_check = session_check


class ServersideOutput(EnrichedOutput):
    """
     Like a normal Output, but with the content stored only server side.
    """


class ServersideOutputTransform(DashTransform):

    def __init__(self, backend=None, session_check=True):
        self.backend = backend if backend is not None else FileSystemStore()
        self.session_check = session_check

    def init(self, dt):
        # Set session secret (if not already set).
        if not dt.server.secret_key:
            dt.server.secret_key = secrets.token_urlsafe(16)

    def apply(self, callbacks):
        # 1) Creat index.
        serverside_callbacks = []
        serverside_output_map = {}
        for callback in callbacks:
            # If memoize keyword is used, serverside caching is needed.
            memoize = callback["kwargs"].get("memoize", None)
            serverside = False
            # Keep tract of which outputs are server side outputs.
            for output in callback[dd.Output]:
                if isinstance(output, ServersideOutput):
                    serverside_output_map[_create_callback_id(output)] = output
                    serverside = True
                # Set default values.
                if not isinstance(output, ServersideOutput) and not memoize:
                    continue
                output.backend = output.backend if output.backend is not None else self.backend
                output.session_check = output.session_check if output.session_check is not None else self.session_check
            # Keep track of server side callbacks.
            if serverside or memoize:
                serverside_callbacks.append(callback)
        # 2) Inject cached data into callbacks.
        for callback in callbacks:
            # Figure out which args need loading.
            items = callback[dd.Input] + callback[dd.State]
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
                    unique_id = _get_cache_id(f, output, list(filtered_args), output.session_check)
                    unique_ids.append(unique_id)
                    if not output.backend.has(unique_id):
                        update_needed = True
                        break
                # If not update is needed, just return the ids (or values, if not serverside output).
                if not update_needed:
                    results = [uid if isinstance(callback[Output][i], ServersideOutput) else
                               callback[Output][i].backend.get(uid) for i, uid in enumerate(unique_ids)]
                    return results if multi_output else results[0]
            # Do the update.
            data = f(*args)
            data = list(data) if multi_output else [data]
            if callable(memoize):
                data = memoize(data)
            for i, output in enumerate(callback[Output]):
                # Skip no_update updates.
                if isinstance(data[i], type(dash.no_update)):
                    continue
                # Replace only for server side outputs.
                serverside_output = isinstance(callback[Output][i], ServersideOutput)
                if serverside_output or memoize:
                    # Filter out Triggers (a little ugly to do here, should ideally be handled elsewhere).
                    is_trigger = trigger_filter(callback["sorted_args"])
                    filtered_args = [arg for i, arg in enumerate(args) if not is_trigger[i]]
                    unique_id = _get_cache_id(f, output, list(filtered_args), output.session_check)
                    output.backend.set(unique_id, data[i])
                    # Replace only for server side outputs.
                    if serverside_output:
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
            children = _as_list(layout.children) + self.hidden_divs
            layout.children = children
            self.initialized = True
        return layout

    def apply(self, callbacks):
        for callback in callbacks:
            if len(callback[dd.Output]) == 0:
                output_id = str(uuid.uuid4())
                hidden_div = html.Div(id=output_id, style={"display": "none"})
                callback[dd.Output] = [dd.Output(output_id, "children")]
                self.hidden_divs.append(hidden_div)
        return callbacks


# endregion

# region Transformer implementations

class Dash(DashProxy):
    def __init__(self, *args, output_defaults=None, **kwargs):
        output_defaults = dict(backend=None, session_check=True) if output_defaults is None else output_defaults
        transforms = [TriggerTransform(), MultiplexerTransform(), NoOutputTransform(),
                      ServersideOutputTransform(**output_defaults)]
        super().__init__(*args, transforms=transforms, **kwargs)

# endregion
