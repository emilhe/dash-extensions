import logging
import threading
from copy import copy
from typing import List, Optional, Tuple, Dict, Callable, Union, FrozenSet, TypeVar, Type, Generator

import dash_core_components as dcc
import dash_html_components as html
from dash import dependencies as dd
from dash.development.base_component import Component, MutableSequence
from flask import current_app

from dash_extensions.enrich import DashTransform

logger = logging.getLogger("composed_component")


class DependencyUnmatched(Exception):
    pass


class DashIdError(Exception):
    pass


class Alias(dd.DashDependency):
    pass


TYPE_NAME = "class"
CHILD_PREFIX = "*"

# represent a wildcard (MATCH, ALL,...)
WildCard = TypeVar("WildCard")
# represent the hash of a component_id
HashComponentId = Union[str, FrozenSet[Tuple[str, Union[str, WildCard]]]]

# represent the dict version of a component id
LongComponentId = Dict[str, str]

# represent a component id
ComponentId = Union[str, LongComponentId]

# represent a generic LongComponentId
GenericComponentId = Dict[str, Union[str, WildCard]]


def id_transformer(
        generic_key: GenericComponentId, component_class: Type[Component]
) -> Callable[[GenericComponentId], GenericComponentId]:
    """Return a function that takes an id (as in a DashDependency) for a component_class
    and resolve it by prepending the scope generic key.
    """

    def wrapper(id: GenericComponentId) -> GenericComponentId:
        id = _get_conform_id(component_class, id)

        return _wrap_child_id(generic_key, id)

    return wrapper


def id_inheriter(component_class) -> Callable[[ComponentId, ComponentId], ComponentId]:
    """Return a function that takes a parent_id and a child_id (of the component_class)
    and create a new fully qualified id. Useful to rewrite the ids of children of a component.

    Convert the child_id to a dict if not yet a dict ({"id":child_id})
    If the component_class is ComposedComponentMixin, then add the TYPE_NAME=component_class to the child_id.
    Combine the parent_id and the child_id with _wrap_child_id

    """

    def wrapper(parent_id, child_id):
        child_id = _get_conform_id(component_class, child_id)

        return _wrap_child_id(parent_id, child_id)

    return wrapper


def _hash_id(component_id: Union[ComponentId, GenericComponentId]) -> HashComponentId:
    return frozenset(_make_id_generic(component_id).items()) if isinstance(component_id, dict) else component_id


def _unhash_id(component_id: HashComponentId) -> Union[ComponentId, GenericComponentId]:
    return dict(component_id) if isinstance(component_id, frozenset) else component_id


def _wrap_child_id(
        parent_id: GenericComponentId, child_id: GenericComponentId, match_parent=False
) -> GenericComponentId:
    """Wrap a component id with the parent id, making the parent generic if match_parent=True."""
    # if a parent_id is the root component, it has a parent_id == {}
    # and does not need to wrap the id of its children, so return child_id unchanged
    if parent_id == {}:
        return child_id

    if isinstance(child_id, str):
        child_id = dict(id=child_id)

    level_child = (max(k.count(CHILD_PREFIX) for k in parent_id) if parent_id else -1) + 1

    return {
        **{f"{CHILD_PREFIX * level_child}{k}": v for k, v in child_id.items()},
        **{
            f"{k}": v
            for k, v in (_make_id_generic(parent_id) if match_parent else parent_id).items()
        },
    }


def _get_conform_id(
        component_class_or_instance: Union[Component, Type[Component]], id: ComponentId = None
) -> LongComponentId:
    is_instance = id is None and isinstance(component_class_or_instance, Component)
    is_class = id is not None and issubclass(component_class_or_instance, Component)
    if not (is_instance or is_class):
        raise ValueError(
            f"You should call with either a composed component class and an id or just a component instance.\n"
            f"You have called it with _get_conform_id({component_class_or_instance},{repr(id)})"
        )

    if is_instance:
        id = component_class_or_instance.id
    klass = component_class_or_instance if is_class else component_class_or_instance.__class__

    # standardize id to a dict
    if isinstance(id, str):
        id = dict(id=id)
    else:
        id = copy(id)

    # if klass is a ComposedComponentMixin, add TYPE_NAME
    if issubclass(klass, ComposedComponentMixin):
        id[TYPE_NAME] = klass.__qualname__

    return id


def _make_id_generic(id: Union[ComponentId, GenericComponentId]) -> GenericComponentId:
    """transform a specific id to a generic one (replacing all non wildcard to MATCH except for TYPE_NAME)"""
    return {
        k: (dd.MATCH if not k.endswith(TYPE_NAME) and not isinstance(v, dd._Wildcard) else v)
        for k, v in id.items()
    }


def _find_simple_children_with_ids(
        component: Component
) -> Generator[Tuple[ComponentId, Component], None, None]:
    """yield recursively the children of component.
    If a ComposedComponentMixin is found, do not recurse into it."""
    children = getattr(component, "children", [])
    if not isinstance(children, (tuple, MutableSequence)):
        children = [children]

    for child in children:
        # if child has an id, yield it
        if hasattr(child, "id"):
            yield child
        # recurse on standard components (not ComposedComponentMixin)
        if not isinstance(child, ComposedComponentMixin):
            yield from _find_simple_children_with_ids(child)


# def app_callback_smartifier(scope:"ComponentScope",app_callback):
#     """Overwrite the standard app.callback by adding the id of the composed component in the State
#     and providing to the function an extra 'wrap' argument that allow wrapping of new elements with
#     ids within a callback (dynamic components).
#
#     @self.callback(Input(),Output(),...)
#     def my_callback(...):
#         ...
#     ==> no change, equivalent to
#     @self._app.callback(Input(),Output(),...)
#     def my_callback(...):
#         ...
#
#
#     @self.callback(Input(),Output(),...)
#     def my_callback(wrap, ...):
#         ...
#     ==> inject wrapper as variable wrap
#     @self._app.callback(Input(),Output(),..., State("self", "id"))
#     def my_callback_wrapper(..., self_id):
#         return my_callback(wrap=lambda component: self.wrap(self_id,component), ...):
#     """
#
#     """should return new app.callback kind of function that wraps a function f"""
#     def new_app_callback(*args, **kwargs):
#         def wrapper(f):
#             # if first argument of function is named 'wrap', then inject in the call a wrapper with
#             # lambda elem: class.wrap(self_id, elem)
#             if next(iter(inspect.signature(f).parameters)) == "wrap":
#                 # callback start with the magic 'wrap' argument
#                 # register with an extra State("self","id")
#                 # a new callback that calls the original callback
#                 def my_callback_wrapper(**kwargs):
#                     self_id = kwargs.pop("self_id")
#                     return f(
#                         wrap=lambda component, self_id=self_id: wrap(self_id, component), **kwargs
#                     )
#
#                 app_callback(*args, State("self", "id"))(my_callback_wrapper)
#             else:
#                 result = app_callback(*args)(f)
#
#             return result
#
#         return wrapper
#
#     return new_app_callback


class ComposedComponentMixin(Component):
    """Mixin to add composability to a given Component (e.g. to an html.Div).

    The composed component declares:
    - its own properties to keep its own state (modelled as dcc.Store subcomponents).
    - its aliased properties that are linked to a property of one of its subcomponents
    - its layout() that returns a 'children' structure with subcomponents having ids that will be mangled (to avoid clash)
    - its declare_callbacks() that register declare_callbacks to orchestrate its subcomponents

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
    - simple-component => {"id": "simple-component", "type": "unique-class-type" }
    - my-subcomponent => {"parent_id": simple-component, "type": "unique-class-type", "child_id": my-subcomponent }
    - my-state        => {"parent_id": simple-component, "type": "unique-class-type", "child_id": my-state }

    This requires the following rewrites regarding declare_callbacks (handle mangling + alias + own properties):
    internal declare_callbacks: replace "self" by a generic MATCH
    - ("self", my-state)  -> ({"parent_id": MATCH, "type": "unique-class-type", "child_id": my-state }, "data")
    - ("self", my-alias)  -> ({"parent_id": MATCH, "type": "unique-class-type", "child_id": my-subcomponent }, "value")
    all non internal declare_callbacks:
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
    _properties: List[str] = []
    # dict of aliases (property name -> component_id.component_property)
    # ie property names that are mapped to properties of internal components
    _aliases: Dict[str, Type[Alias]] = {}
    # original id before mangling to make it pattern matchable
    _original_id: ComponentId

    def __repr__(self):
        return f"{self.__class__.__name__}(id='{self.id}')"

    @classmethod
    def _validate_aliases(
            cls, aliases: Dict[str, Type[Alias]], properties: List[str]
    ) -> Dict[str, Type[Alias]]:
        # handle validation and default
        if not (
                isinstance(aliases, dict)
                and all(isinstance(k, str) and isinstance(v, Alias) for k, v in aliases.items())
        ):
            raise ValueError(
                f"The _aliases of {cls.__qualname__} with id={id} should be a dict {{ alias_prop -> Alias(id, aliased_prop) }}\n"
                f"Current value of _aliases is {aliases}"
            )
        aliases_with_properties = aliases.copy()

        # check property not defined in both aliases and properties
        if set(properties).intersection(aliases_with_properties):
            raise ValueError(
                f"Error in class {cls.__qualname__} as some owned properties ({properties}) have the same name "
                f"as some aliased properties ({list(aliases_with_properties)})"
            )

        # create own properties as aliases to Store components
        # and insert them at the beginning of a copy of the _aliases dict to be able to use them in the other aliases
        aliases_with_properties = {
            **{k: Alias(k, "data") for k in properties},
            **aliases_with_properties,
        }
        logger.info(
            f"alias transformation from {aliases} + {properties} to {aliases_with_properties}"
        )

        return aliases_with_properties

    def __init__(self, *, id, layout_kwargs={}, **kwargs):
        # backup original id
        self._original_id = copy(id)

        # handle _properties
        self._properties = copy(self._properties)

        # handle _aliases
        self._aliases = self._validate_aliases(aliases=self._aliases, properties=self._properties)

        # list all component properties and retrieve default values
        properties = {k: kwargs.pop(k, None) for k in list(self._aliases)}
        # get layout by passing the initial values given for own properties and aliases
        layout = self.layout(**layout_kwargs, **properties)
        # normalise the layout to list to be able to self._states at the end
        if not isinstance(layout, list):
            layout = [layout]

        # create component by combining given layout and added component states
        super().__init__(
            id=id,
            children=layout + [dcc.Store(id=k, data=properties[k]) for k in self._properties],
            # **kwargs,
        )

    def layout(self, **kwargs):
        """Return a layout that will be assigned to the 'children' property of the composed component.

        Called during __init__
        """
        return []

    @classmethod
    def declare_callbacks(cls):
        """Declare the declare_callbacks on the component. Use 'self' as property_id to refer
        to the component properties.

        Called during callback registration
        """
        pass

    def register_components_explicitly(self):
        """Return component that may have not been declared in layout (because they are dynamically added
        in callbacks or conditionally added in layout).

        Should return instantiated component with the right id structure.

        Called before callback registration to complete ComponentScope
        """
        return []

    @classmethod
    def callback(cls, *args, **kwargs):
        def wrapper(f):
            cls._callbacks.append((args, kwargs, f))

        return wrapper

    @classmethod
    def _register_callbacks(cls, callback_decorator):
        cls._callbacks = []
        cls.declare_callbacks()

        if cls._callbacks and isinstance(cls._callbacks[0], tuple):
            # case callback declared via cls.callback
            callbacks = [
                callback_decorator(*args, **kwargs)(cb) for args, kwargs, cb in cls._callbacks
            ]
        else:
            # case callback declared via app.callback (for RootComponent)
            callbacks = cls._callbacks
        return callbacks


def get_root_component(layout, callbacks):
    callbacks = list(callbacks)

    class RootComponent(ComposedComponentMixin, html.Div):
        """Singleton representing the root component of an app"""

        def layout(self, **kwargs):
            return layout

        @classmethod
        def declare_callbacks(cls):
            cls._callbacks = callbacks
            return callbacks

    return RootComponent(id="root")


class ComponentScope:
    """An object uniquely identifying a generic scope for a ComposedComponentMixin.

    It has:
    - a ComposedComponentMixin class (except for root layout)
    - a generic key
    - a flat list of ComponentScope
    - a map between locally scopes ids and a function that convert it to a generic key

    It can:
    - attach to a ComposedComponentMixin (each CCM should be linked to its Scope) or raise Error if can't do it
    - register callbacks of its ComposedComponentMixin for the given generic key


    It is created by:
    - giving an app.Layout and recursively create the ComponentScopes
    """

    _level: int  # 0=root, 1=1 level below root, ...
    _cc_class = Type[ComposedComponentMixin]
    _generic_key: GenericComponentId
    _parent_scope: Optional["ComponentScope"]
    _children_scopes: Dict[HashComponentId, "ComponentScope"]
    _children_ids: List[Tuple[ComponentId, "ComponentScope"]]  # [(original_id, scope),...]
    _map_local_to_generic = Dict[HashComponentId, Callable[[ComponentId], ComponentId]]
    _map_childid_to_fullid = Dict[HashComponentId, Callable[[ComponentId], ComponentId]]
    _aliases_resolved = Dict[str, dd.DashDependency]

    # @classmethod
    # def _get_root_composed_components(cls, layout) -> List["ComposedComponentMixin"]:
    #     if isinstance(layout, ComposedComponentMixin):
    #         root_ccs = [layout]
    #     else:
    #         root_ccs = [
    #             comp
    #             for comp in (_find_simple_children_with_ids(layout))
    #             if isinstance(comp, ComposedComponentMixin)
    #         ]
    #     return root_ccs

    @classmethod
    def create_from_cc(
            cls, parent_scope: Optional["ComponentScope"], component: ComposedComponentMixin
    ) -> "ComponentScope":

        cc_class = component.__class__
        cc_id = _get_conform_id(component)

        if parent_scope:
            generic_key = _make_id_generic(_wrap_child_id(parent_scope._generic_key, cc_id))
            level = parent_scope._level + 1
        else:
            generic_key = {}
            level = 0

        children_ids = []
        children_scopes = {}
        map_local_to_generic = {}
        map_childid_to_fullid = {}
        aliases_resolved = {}

        # create related scope
        scope = cls(
            level,
            cc_class,
            generic_key,
            parent_scope,
            children_scopes,
            map_local_to_generic,
            map_childid_to_fullid,
            children_ids,
            aliases_resolved,
        )

        # look for components to scope
        components_to_scopify = (
                list(_find_simple_children_with_ids(component))
                + component.register_components_explicitly()
        )

        child_component_id_duplicate_tracker = {}

        # fill in collections of scope
        for child_component in components_to_scopify:
            child_component_id = _make_id_generic(child_component.id) if isinstance(child_component.id,dict) else child_component.id
            hash_child_component_id = _hash_id(child_component.id)

            if hash_child_component_id in child_component_id_duplicate_tracker:
                if child_component_id_duplicate_tracker[hash_child_component_id] != child_component.__class__:
                    raise DashIdError(f"Two components have the same id structure (keys={list(child_component.id.keys())})"
                                      f" yet different classes {child_component_id_duplicate_tracker[hash_child_component_id]} <> {child_component.__class__}.\n"
                                      f"Change the id structure so that each class has a different one "
                                      f"(for instance, do not use {{'type': 'my-class', 'index':'my-id'}} but {{'my-class-index':'my-id'}})")

            child_component_id_duplicate_tracker[hash_child_component_id] = child_component.__class__

            # only handle ComposedComponentMixin
            if not isinstance(child_component, ComposedComponentMixin):
                children_ids.append((child_component_id, None))
                continue
            # create transformer converting the id to the fully resolved id
            map_local_to_generic[hash_child_component_id] = id_transformer(
                generic_key=generic_key, component_class=child_component.__class__
            )
            map_childid_to_fullid[hash_child_component_id] = id_inheriter(
                component_class=child_component.__class__
            )

            # recurse if ComposedComponentMixin
            if isinstance(child_component, ComposedComponentMixin):
                # get the child scope
                child_composed_scope = cls.create_from_cc(
                    parent_scope=scope, component=child_component
                )

                # if the child scope is already existing for the parent scope, merge it
                # otherwise, add it
                if _hash_id(child_composed_scope._generic_key) in children_scopes:
                    # there is already a key for such component, merge the new child_composed_scope
                    # with the existing one
                    existing_composed_scope = children_scopes[
                        _hash_id(child_composed_scope._generic_key)
                    ]
                    # merge mappings
                    for map_name in [
                        "_map_local_to_generic",
                        "_children_scopes",
                        "_map_childid_to_fullid",
                        "_aliases_resolved",
                    ]:
                        getattr(existing_composed_scope, map_name).update(
                            getattr(child_composed_scope, map_name)
                        )
                    # merge _children_ids mapping (as a list of (id,scope))
                    existing_composed_scope._children_ids.extend(
                        [
                            elem
                            for elem in child_composed_scope._children_ids
                            if elem not in existing_composed_scope._children_ids
                        ]
                    )
                    # link child to existing child
                    child_composed_scope = existing_composed_scope
                else:
                    children_scopes[
                        _hash_id(child_composed_scope._generic_key)
                    ] = child_composed_scope

            # add id to list of children ids
            children_ids.append((child_component_id, child_composed_scope))

        # handle aliases
        for k, v in component._aliases.items():
            aliases_resolved[k] = v

        return scope

    def __init__(
            self,
            level,
            cc_class,
            generic_key,
            parent_scope,
            children_scopes,
            map_local_to_generic,
            map_childid_to_fullid,
            children_ids,
            aliases_resolved,
    ):
        assert isinstance(generic_key, dict)
        assert issubclass(cc_class, ComposedComponentMixin)
        self._level = level
        self._cc_class = cc_class
        self._generic_key = generic_key
        print("generic_key", generic_key)
        self._parent_scope = parent_scope
        self._children_scopes = children_scopes
        self._map_local_to_generic = map_local_to_generic
        self._map_childid_to_fullid = map_childid_to_fullid
        self._children_ids = children_ids
        self._aliases_resolved = aliases_resolved
        self.log(f"creating Scope {cc_class.__qualname__}({generic_key})")

    def log(self, msg):
        logger.info("\t" * self._level + msg)

    def map_local_id(self, component_id: GenericComponentId) -> GenericComponentId:
        """Map a local id used in a Dependency to a generic id"""
        self.log(
            f"mapping {component_id} given {self._children_ids}\n\t\t\t\tand aliases {self._aliases_resolved}"
        )
        if component_id == "self":
            return self._generic_key
        try:
            return self._map_local_to_generic[_hash_id(component_id)](component_id)
        except KeyError:
            pass

        # not explicit match, check for PATTERN in children_ids
        _id, _scope = self.map_local_id_to_scope(component_id)
        if _scope is None:
            return _wrap_child_id(parent_id=self._generic_key, child_id=component_id)
        else:
            return self._map_local_to_generic[_hash_id(_id)](component_id)

    def map_local_id_to_scope(self, component_id: GenericComponentId) -> Optional["ComponentScope"]:
        for id, scope in self._children_ids:
            if Alias(id, "dummy") == Alias(component_id, "dummy"):
                return id, scope

        raise DashIdError(f"Could not find scope related to id '{component_id}'")

    def register_callbacks(self, callback_decorator):
        """Register callbacks related to the scope and adapt the callbacks for local ids used to resolved ids.
        Use the callback_decorator to register the callback re the real Dash app.
        Apply recursively to children ComposedComponentMixin
        """

        # if not a root non ComposedComponentMixin class
        assert issubclass(self._cc_class, ComposedComponentMixin)
        self.log(
            f"registering callbacks for {self._cc_class.__qualname__} with key = {self._generic_key}"
        )
        # create new callbacks for the scope
        self.callbacks = self._cc_class._register_callbacks(callback_decorator)

        self.log(
            f"rewriting {len(self.callbacks)} callbacks for {self._cc_class.__qualname__} with key = {self._generic_key}"
        )
        # recurse on children scopes
        for child_scope in self._children_scopes.values():
            child_scope.register_callbacks(callback_decorator)

        return self.callbacks

    def rewrite_callback_dependencies(self, ):

        # adapt callbacks
        for cb in self.callbacks:
            self.log(f"rewriting callback {cb['f']}")
            for dep in cb["sorted_args"]:
                # rename local dep.component_id to resolved dep.component_id
                dep_original = copy(dep)
                self.resolve_dependency(dep)
                self.log(f"- rewriting dependency from {dep_original} to {dep}")

        # recurse on children scopes
        for child_scope in self._children_scopes.values():
            child_scope.rewrite_callback_dependencies()

    def resolve_dependency(self, dep: dd.DashDependency):
        if dep.component_id == "self":
            if dep.component_property in self._aliases_resolved:
                new_dep = copy(self._aliases_resolved[dep.component_property])
                new_dep.__class__ = dep.__class__
                self.resolve_dependency(new_dep)
            else:
                new_dep = Alias(self._generic_key, dep.component_property)
        else:
            # find the scope related to the id (raise error if not found)
            _, scope_dep = self.map_local_id_to_scope(dep.component_id)
            if scope_dep is None:
                # leaf, add the generic key of the scope
                new_dep = Alias(
                    _wrap_child_id(self._generic_key, dep.component_id), dep.component_property
                )
            else:
                new_dep = copy(dep)
                new_dep.component_id = "self"
                scope_dep.resolve_dependency(new_dep)
                if self._level == 0:
                    # root, bind the id:MATCH to id:component_id
                    new_dep.component_id.update(id=dep.component_id)
                else:
                    # in composed component, bind the ids of the element
                    new_dep.component_id.update(**self.map_local_id(dep.component_id))

        dep.component_id = copy(new_dep.component_id)
        dep.component_property = new_dep.component_property

    def adapt_ids(self, component: ComposedComponentMixin):
        """Adapt ids of component related to scope"""

        self.log(f"replacing ids of children of {component} - level {self._level}")
        for child_component in _find_simple_children_with_ids(component):
            _, child_scope = self.map_local_id_to_scope(child_component.id)

            # resolve the child id in function of the parent
            child_id_conform = (
                _get_conform_id(child_component) if child_scope else child_component.id
            )
            if self._level >= 1:
                # wrap child id with parent
                resolved_id = _wrap_child_id(parent_id=component.id, child_id=child_id_conform)
            elif self._level == 0:
                # conform to id as first level
                resolved_id = child_id_conform

            # resolved_id = self.map_child_id(parent_id=component.id, child_id=child_id)
            self.log(f"id {child_component.id} replaced by {resolved_id}")
            child_component.id = resolved_id

            # if the component is a ComposedComponentMixin leaf
            # run recursively after finding the right scope
            if child_scope:
                self.log(f"recursing on children of {child_component}")
                child_scope.adapt_ids(child_component)
        self.log(f"replacing done for ids of children of {component}")

    # def to_yaml(self):
    #     def clean_value(v):
    #         if v is MATCH:
    #             return "MATCH"
    #         if isinstance(v, str):
    #             return v
    #         return v.__name__
    #
    #     return {
    #         f"{self._cc_class.__name__}({({k: clean_value(v) for k, v in self._generic_key.items()})})": [
    #             cc.to_yaml() for cc in self._children_scopes.values()
    #         ]
    #     }


class ComposedComponentTransform(DashTransform):
    """Rewrite callback dependencies for composed components"""

    def __init__(self, app):
        # keep reference to the Dash app
        self._app = app

        # store (__class__, generic_key) of composed components already declared
        self._callbacks_declared = set()

        # create lock to manipulate self._callbacks_declared
        self._callbacks_declared_lock = threading.Lock()

    def apply(self, callbacks):
        logger.info(f"start 'apply' phase with {len(callbacks)} callbacks")

        root_cc = get_root_component(self._app.layout, callbacks)
        self._app.layout = root_cc
        root_scope = self._root_scope = ComponentScope.create_from_cc(None, root_cc)
        root_scope.register_callbacks(callback_decorator=self._app.callback)
        root_scope.rewrite_callback_dependencies()
        root_scope.adapt_ids(component=root_cc)
        return callbacks

    def find_scope_for_id(self, composed_component_id: LongComponentId) -> ComponentScope:
        # recursively look for the scope related to the composed_component_id
        def helper(scope: ComponentScope):
            # check if some direct children scope has a matching id
            for hashed_id, child_scope in scope._children_scopes.items():
                if Alias(composed_component_id, "dummy") == Alias(_unhash_id(hashed_id), "dummy"):
                    return child_scope

            # if not, check in all children scopes if there is a match
            for child_scope in scope._children_scopes.values():
                try:
                    return helper(child_scope)
                except DashIdError:
                    pass

            raise DashIdError(f"Could not find scope related to id '{composed_component_id}'")

        # start with root scope
        return helper(self._root_scope)


def wrap(parent_id: LongComponentId, component: Component):
    """Wrap a component by rewriting its id according to the parent id. To be used when creating Components within a
    ComposedComponentMixin callback."""
    try:
        # retrieve composed_component_transform from current_app
        # (raise error if not in the context of a Flask request)
        composed_component_transform: ComposedComponentTransform = current_app.dash_app._composed_component_transform
    except RuntimeError:
        raise ValueError(f"ComposedComponentMixin.wrap() can only used within a Dash callback.")

    # backup id
    if not hasattr(component, "_original_id"):
        component._original_id = component.id

    # wrap id
    component.id = _wrap_child_id(parent_id=parent_id, child_id=_get_conform_id(component))

    try:
        if isinstance(component, ComposedComponentMixin):
            # if the component is a ComposedComponentMixin, we need to rewrite the ids of the internal components
            # if none can be found (DashIdError), then raise value about the component not being registered
            component_scope = composed_component_transform.find_scope_for_id(component.id)

            # cascade rewrite of children of component
            component_scope.adapt_ids(component)

    except DashIdError:
        id_msg = {
            k: "any" for k, v in component.id.items() if k != TYPE_NAME
        }
        msg = (
            f"The component {component} has not yet its callback registered. It is probably "
            f"because its has been added dynamically.\n"
            f"You need to add\n"
            f"cc.register_composed_component({component.__class__.__name__}(id={id_msg}))\n"
            f"after you Dash app declaration."
        )
        raise TypeError(msg)

    return component
