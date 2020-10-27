import functools
import hashlib
import json
import pickle
import secrets
import threading
import uuid

import dash
import dash.dependencies as dd
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from flask import session
from flask_caching.backends import FileSystemCache
from more_itertools import unique_everseen, flatten


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
                                multi_output = any(
                                    [
                                        component_id[k] in [dd.ALLSMALLER, dd.ALL]
                                        for k in component_id
                                    ]
                                )
                        callback[key].append(element)
                        arg_order.append(element)
        if not multi_output:
            multi_output = len(callback[Output]) > 1
        # Save the kwargs for later.
        callback["kwargs"] = kwargs
        callback["sorted_args"] = arg_order
        callback["multi_output"] = multi_output
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
            super().callback(outputs, callback[Input], callback[State], **callback["kwargs"])(
                callback["f"]
            )
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
    inputs_args = [item for item in args if isinstance(item, Input) or isinstance(item, State)]
    is_trigger = [isinstance(item, Trigger) for item in inputs_args]
    return is_trigger


# endregion


# region ComposedComponent transform

class ComposedComponentMixin(Component):
    """Mixin to add composability to a given Component (e.g. to an html.Div).

    The composed component declares:
    - its own properties to keep its own state (modelled as dcc.Store subcomponents).
    - its aliased properties that are linked to a property of one of its subcomponents
    - its layout() that returns a 'children' structure with subcomponents having ids that will be mangled (to avoid clash)
    - its declare_callbacks() that register callbacks to orchestrate its subcomponents

    The simplest form of a composed component would be:
    - id: simple-component
      - children:
        - id: my-subcomponent  -> another dash component
        - id: my-state  -> dcc.Store
      - properties:
        - own property      ==> ("self", my-state)  -> (my-state, "data")
          (declared as _properties = ["my-state"])
        - aliased property  ==> ("self", my-alias)  -> (my-subcomponent, "value")
          (declared as _aliases = {"my-alias": (id, property) ])


    This requires the following rewrites regarding components ids (mangling):
    - my-subcomponent => {"parent_id": simple-component, "type": "unique-class-type", "child_id": my-subcomponent }
    - my-state        => {"parent_id": simple-component, "type": "unique-class-type", "child_id": my-state }

    This requires the following rewrites regarding callbacks (handle mangling + alias + own properties):
    internal callbacks: replace "self" by a generic MATCH
    - ("self", my-state)  -> ({"parent_id": MATCH, "type": "unique-class-type", "child_id": my-state }, "data")
    - ("self", my-alias)  -> ({"parent_id": MATCH, "type": "unique-class-type", "child_id": my-subcomponent }, "value")
    all non internal callbacks:
    - (simple-component, my-state)  -> ({"parent_id": simple-component, "type": "unique-class-type", "child_id": my-state }, "data")
    - (simple-component, my-alias)  -> ({"parent_id": simple-component, "type": "unique-class-type", "child_id": my-subcomponent }, "value")

    When the id of a component/sub-component is not a string but a dict, we should prepend to the keys of the dict the
    "parent_" or "child_" prefix. For the {"parent_id": MATCH}, it should be extended to {"parent_key1": MATCH, "parent_key2": MATCH, ...}

    Example of a more complex form of a composed component with non string ids would be
    - id: {"index": "composedcomponent1"}
      - id: {"index": "my-subcomposedcomponent1"}
      - id: {"index": "my-subcomposedcomponent2"}
      - id: {"index": "my-state"}

    """

    # list of property names to be created to store the state of this component
    _properties = Component.UNDEFINED
    # dict of aliases (property name -> component_id.component_property)
    # ie property names that are mapped to properties of internal components
    _aliases = Component.UNDEFINED
    # string with the type of the composed component (used to mangle the id of the subcomponents
    _composed_type = Component.UNDEFINED

    def _mangle_component_property(self, child_id, parent_match=None):
        return ComposedComponentTransform._mangle_id(
            composed_type=self._composed_type,
            parent_id=self.id,
            child_id=child_id,
            parent_match=parent_match)

    def __init__(self, id, **kwargs):
        # handle _properties
        if self._properties is Component.UNDEFINED:
            self._properties = []

        # handle _aliases
        if self._aliases is Component.UNDEFINED:
            self._aliases = {}

        if not isinstance(self._composed_type, str):
            raise ValueError(
                f"The '_composed_type' of {self} should be a string, not {self._composed_type}"
            )

        # create Store components for component properties (mangle name to avoid id conflicts)
        prop_values = {k: kwargs.pop(k, None) for k in self._properties}
        self._states = [dcc.Store(id=k, data=v) for k, v in prop_values.items()]
        alias_values = {k: kwargs.pop(k, None) for k in self._aliases}

        # get layout by passing the initial values given for own properties and aliases
        layout = self.layout(**prop_values, **alias_values)
        # normalise the layout to list
        if not isinstance(layout, list):
            layout = [layout]

        # create component by combining given layout and added component states
        super().__init__(id=id, children=layout + self._states, **kwargs)

        # mangle ids of subcomponents to avoid clash and allow MATCHing
        for comp_with_id in self._traverse_ids():
            comp_with_id.id = self._mangle_component_property(comp_with_id.id)

    def layout(self, **kwargs):
        """Return a layout that will be assigned to the 'children' property of the composed component."""
        raise NotImplementedError

    def declare_callbacks(self, app):
        """Declare the callbacks on the component. Use 'self' as property_id to refer
        to the component properties."""
        raise NotImplementedError


class ComposedComponentTransform(DashTransform):
    """Rewrite callback dependencies for composed components"""
    TYPE_NAME = "composed_type"

    @classmethod
    def _prefix_id(cls, id, prefix):
        if isinstance(id, str):
            id = dict(id=id)
        return {f"{prefix}_{k}": v for k, v in id.items()}

    @classmethod
    def _mangle_id(cls, parent_id, child_id, composed_type, parent_match=None):
        """Return a mangled id with dict structure:
        type -> composed_type
        parent_id (if str) -> {"parent_id": parent_id} if not parent_match else {"parent_id": parent_match}
        parent_id (if dict) -> {"parent_key1": parent_value1, "parent_key2": parent_value2, } if not parent_match
                               else {"parent_key1": parent_match, "parent_key2": parent_match, }
        and same for child_id (except no logic for parent_match)
        """

        if parent_match:
            return {cls.TYPE_NAME: composed_type, **{k: parent_match for k in cls._prefix_id(parent_id, "parent")},
                    **cls._prefix_id(child_id, "child")}
        else:
            return {cls.TYPE_NAME: composed_type, **cls._prefix_id(parent_id, "parent"),
                    **cls._prefix_id(child_id, "child")}

    def __init__(self, app):
        # keep reference to the dash app
        self._app = app

        # store __class__ of composed components already declared
        self._callbacks_declared = set()
        # create lock to manipulate self._callbacks_declared
        self._callbacks_declared_lock = threading.Lock()

    def _process_composedcomponent_internal_callbacks(self, composed_components):
        callbacks = self._app.callbacks

        # for each composed component, register the callbacks and postprocess their args
        for comp in composed_components:
            assert isinstance(comp, ComposedComponentMixin)

            with self._callbacks_declared_lock:
                # check if callbacks already declared (if so, skip the component)
                if comp.__class__ in self._callbacks_declared:
                    continue

                # mark the type as being already declared
                self._callbacks_declared.add(comp.__class__)

            # store the length of the callbacks list to be able to detect afterwards which callbacks have been added
            ncallbacks = len(callbacks)

            # call the ComposedComponent `declare_callbacks` that will add to the app its own callbacks
            comp.declare_callbacks(self._app)

            # process each new callback (registered by the ComposedComponentMixin)
            # to mangle the arguments referring to internal components and transform 'self' references
            new_callbacks = callbacks[ncallbacks:]
            for callback in new_callbacks:
                for prop in callback["sorted_args"]:
                    if prop.component_id == "self":
                        if prop.component_property in comp._properties:
                            # manage self new properties
                            prop.component_id = comp._mangle_component_property(child_id=prop.component_property,
                                                                                parent_match=dd.MATCH)
                            prop.component_property = "data"
                        else:
                            # manage aliases
                            _id, _prop = comp._aliases[prop.component_property]
                            prop.component_id = comp._mangle_component_property(child_id=_id,
                                                                                parent_match=dd.MATCH)
                            prop.component_property = _prop
                    else:
                        # manage mangling of subcomponents
                        prop.component_id = comp._mangle_component_property(child_id=prop.component_id,
                                                                            parent_match=dd.MATCH)

    def apply(self, callbacks):
        # assign the dash app to the flask server to be able to retrieve the dash app from a current_app
        # self._app.server.dash_app = self._app

        """add callbacks from composed elements"""

        composed_components_with_ids = [comp for comp in self._app.layout._traverse_ids() if
                                        isinstance(comp, ComposedComponentMixin)]

        self._process_composedcomponent_internal_callbacks(
            [comp for comp in composed_components_with_ids]
        )

        # rewrite all arguments of callbacks that refers to properties of ComposedComponent
        map_dependency_original2translated = [
                                                 # handle own properties
                                                 (dd.DashDependency(comp.id, own_prop),
                                                  lambda dependency, child_id=own_prop, type=comp._composed_type: (
                                                      ComposedComponentTransform._mangle_id(
                                                          parent_id=dependency.component_id,
                                                          child_id=child_id,
                                                          composed_type=type),
                                                      "data"))
                                                 for comp in composed_components_with_ids
                                                 for own_prop in comp._properties
                                             ] + [
                                                 # handle aliased properties
                                                 (dd.DashDependency(comp.id, alias_prop),
                                                  lambda dependency, child_id=subid, type=comp._composed_type,
                                                         subprop=subprop: (
                                                      ComposedComponentTransform._mangle_id(
                                                          parent_id=dependency.component_id,
                                                          child_id=child_id,
                                                          composed_type=type),
                                                      subprop))
                                                 for comp in composed_components_with_ids
                                                 for alias_prop, (subid, subprop) in comp._aliases.items()
                                             ]

        # convert properties linked to data stores
        for callback in callbacks:
            for prop in callback["sorted_args"]:
                # look if prop matches a "to translate" property
                for (prop_original, prop_translated) in map_dependency_original2translated:
                    if prop_original == prop:
                        # if match, translate the property
                        prop.component_id, prop.component_property = prop_translated(prop)
                        break

        return callbacks


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
    multi_output = any([callback["multi_output"] for callback in callbacks])
    if not multi_output:
        all_outputs = []
        for callback in callbacks:
            all_outputs += callback[Output]
        multi_output = len(list(set(all_outputs))) > 1

    # TODO: There might be a scope issue here
    def wrapper(*args):
        local_inputs = list(args)[: len(inputs)]
        local_states = list(args)[len(inputs):]
        if len(dash.callback_context.triggered) == 0:
            raise PreventUpdate
        prop_id = dash.callback_context.triggered[0]["prop_id"]
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
                if not callbacks[i][
                    "multi_output"
                ]:  # len(callbacks[i][Output]) == 1:  TODO: Is this right?
                    outputs_i = [outputs_i]
                for j, item in enumerate(outputs_i):
                    output_values[output_mappings[i][j]] = outputs_i[j]
            except PreventUpdate:
                continue
        # Check if an update is needed.
        if all([item == dash.no_update for item in output_values]):
            raise PreventUpdate
        # Return the combined output.
        return (
            output_values if multi_output else output_values[0]
        )  # TODO: Check for multi output here?

    return {
        Output: outputs,
        Input: inputs,
        "f": wrapper,
        State: states,
        "kwargs": kwargs,
        "multi_output": multi_output,
    }


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


class Output(dd.Output):
    """
     Like a normal Output, includes additional properties related to storing the data.
    """

    def __init__(self, component_id, component_property, backend=None, session_check=None):
        super().__init__(component_id, component_property)
        self.backend = backend
        self.session_check = session_check


class ServersideOutput(Output):
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
            for output in callback[Output]:
                if isinstance(output, ServersideOutput):
                    serverside_output_map[_create_callback_id(output)] = output
                    serverside = True
                # Set default values.
                if not isinstance(output, ServersideOutput) and not memoize:
                    continue
                output.backend = output.backend if output.backend is not None else self.backend
                output.session_check = (
                    output.session_check if output.session_check is not None else self.session_check
                )
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
    memoize = callback["kwargs"].pop("memoize", None)

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
            for i, output in enumerate(callback[Output]):
                serverside_output = isinstance(callback[Output][i], ServersideOutput)
                # Replace only for server side outputs.
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
    def __init__(self, *args, output_defaults=None, **kwargs):
        output_defaults = (
            dict(backend=None, session_check=True) if output_defaults is None else output_defaults
        )

        transforms = [
            TriggerTransform(),
            ComposedComponentTransform(app=self),
            NoOutputTransform(),
            GroupTransform(),
            ServersideOutputTransform(**output_defaults),
        ]
        super().__init__(*args, transforms=transforms, **kwargs)
        self.server.dash_app = self

# endregion
