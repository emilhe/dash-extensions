import inspect
import logging
import threading
from collections import defaultdict
from copy import deepcopy, copy

import dash_core_components as dcc
import yaml
from dash import dependencies as dd
from dash.development.base_component import Component
from flask import current_app

from enrich import DashTransform, State, Output

logger = logging.getLogger("composed_component")


# region ComposedComponent transform


def _rewrite_children_ids(composed_component):
    """Inject into the id of all direct children component, its own ids and prefix with "child_" all the
    ids of its children"""
    for child in composed_component.children_composed_component:
        # save original id for further mapping in declare_callbacks
        if not hasattr(child, "_original_id"):
            child._original_id = child.id

        rewritten_id = _wrap_child_id(composed_component.id, child.id)

        logger.info(f"id rewriting from {composed_component} -> {child.id} to {rewritten_id}")

        child.id = rewritten_id

        # recurse for ComposedComponentMixin
        if isinstance(child, ComposedComponentMixin):
            _rewrite_children_ids(child)


def wrap(parent_id, component):
    """Wrap a component by rewriting its id according to the parent id"""
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
    component.id = _wrap_child_id(parent_id=parent_id, child_id=component.id)

    # cascade rewrite of children of component
    _rewrite_children_ids(component)

    ############## check that current component has its declare_callbacks already defined

    # check declare_callbacks for component have been registered
    # if there are added dynamically (ie current_app.xxx does not raise a RuntimeError)
    if not composed_component_transform.is_component_already_registered(
            composed_component=component
    ):
        id_msg = {
            k: "any" for k, v in component.id.items() if k != composed_component_transform.TYPE_NAME
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


def _wrap_child_id(parent_id, child_id, match_parent=False):
    """Wrap a component id with the parent id."""
    if isinstance(child_id, str):
        child_id = dict(id=child_id)

    CHILD_PREFIX = "child_"

    level_child = max(k.count(CHILD_PREFIX) for k in parent_id) + 1

    return {
        **{f"{CHILD_PREFIX * level_child}{k}": v for k, v in child_id.items()},
        **{
            f"{k}": v
            for k, v in (_make_id_generic(parent_id) if match_parent else parent_id).items()
        },
    }


def _make_id_generic(id):
    """transform a specific id to a generic one (replacing all non wildcard to MATCH except for TYPE_NAME)"""
    return {
        k: (
            dd.MATCH
            if not k.endswith(ComposedComponentTransform.TYPE_NAME)
               and not isinstance(v, dd._Wildcard)
            else v
        )
        for k, v in id.items()
    }


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
    _properties = Component.UNDEFINED
    # dict of aliases (property name -> component_id.component_property)
    # ie property names that are mapped to properties of internal components
    _aliases = Component.UNDEFINED
    # string with the type of the composed component (used to mangle the id of the subcomponents
    _composed_type = Component.UNDEFINED
    # original id before mangling to make it pattern matchable
    _original_id = None

    @classmethod
    def normalize_id(cls, id):
        if cls._composed_type is Component.UNDEFINED:
            raise ValueError(
                f"The '_composed_type' of {cls.__class__} is not specified. "
                f"Please assign it in your class to a unique string."
            )
        if not isinstance(cls._composed_type, str):
            raise ValueError(
                f"The '_composed_type' of {cls} should be a string, not {cls._composed_type}"
            )

        # convert the id to a dict structure and add the _composed_type
        if isinstance(id, str):
            id = dict(id=id)
        else:
            assert isinstance(id, dict)
            assert ComposedComponentTransform.TYPE_NAME not in id
            id = id.copy()
        id[ComposedComponentTransform.TYPE_NAME] = cls._composed_type

        return id

    def get_generic_key(self):
        return (self.__class__, frozenset(_make_id_generic(self.id).items()))
        return (self.__class__.__qualname__, frozenset(_make_id_generic(self.id).items()))

    def __init__(self, *, id, **kwargs):
        # handle _properties
        if self._properties is Component.UNDEFINED:
            self._properties = []

        # handle _aliases
        if self._aliases is Component.UNDEFINED:
            self._aliases = {}
        else:
            if not (
                    isinstance(self._aliases, dict)
                    and all(
                isinstance(k, str) and isinstance(v, Alias) for k, v in self._aliases.items()
            )
            ):
                raise ValueError(
                    f"The _aliases of {self.__class__.__qualname__} with id={id} should be a dict {{ alias_prop -> Alias(id, aliased_prop) }}\n"
                    f"Current value of _aliases is {self._aliases}"
                )
            self._aliases = self._aliases.copy()

        # check property not defined in both _aliases and _properties
        if set(self._properties).intersection(self._aliases):
            raise ValueError(
                f"Some owned properties ({self._properties}) have the same name "
                f"as some aliased properties ({list(self._aliases)})"
            )

        # save _original_id to map it to the new id
        self._original_id = id

        # convert the id to a dict structure and add the _composed_type
        id = self.normalize_id(id)

        # list all component properties and retrieve default values
        properties = {k: kwargs.pop(k, None) for k in (self._properties + list(self._aliases))}

        # create Store components for component properties
        self._states = [dcc.Store(id=k, data=properties[k]) for k in self._properties]

        # create own properties as aliases to Store components
        # and insert them at the beginning of a copy of the _aliases dict to be able to use them in the other aliases
        self._aliases = {
            **{k: Alias(k, "data") for k in self._properties},
            **deepcopy(self._aliases),
        }

        # get layout by passing the initial values given for own properties and aliases
        layout = self.layout(**properties)
        # normalise the layout to list to be able to self._states at the end
        if not isinstance(layout, list):
            layout = [layout]

        # create component by combining given layout and added component states
        super().__init__(id=id, children=layout + self._states, **kwargs)

        logger.debug(f"normalisation of id from {self._original_id} to {self.id}")

        # assign parent_composed_component to direct children
        # and add the direct children to self.children_composed_component
        self.children_composed_component = []
        for comp_with_id in self._traverse_ids():
            # attribute parent_composed_component to children that have not yet the attribute
            # (ie direct children as others will have the attribute already set by their own parent)
            if not hasattr(comp_with_id, "parent_composed_component"):
                comp_with_id.parent_composed_component = self
                self.children_composed_component.append(comp_with_id)

    def layout(self, **kwargs):
        """Return a layout that will be assigned to the 'children' property of the composed component."""
        raise NotImplementedError

    def declare_callbacks(self):
        """Declare the declare_callbacks on the component. Use 'self' as property_id to refer
        to the component properties.
        """
        raise NotImplementedError

    def callback(self, *args, **kwargs):
        """Overwrite the standard app.callback by adding the id of the composed component in the State
        and providing to the function an extra 'wrap' argument that allow wrapping of new elements with
        ids within a callback (dynamic components).

        @self.callback(Input(),Output(),...)
        def my_callback(...):
            ...
        ==> no change, equivalent to
        @self._app.callback(Input(),Output(),...)
        def my_callback(...):
            ...


        @self.callback(Input(),Output(),...)
        def my_callback(wrap, ...):
            ...
        ==> inject wrapper as variable wrap
        @self._app.callback(Input(),Output(),..., State("self", "id"))
        def my_callback_wrapper(..., self_id):
            return my_callback(wrap=lambda component: self.wrap(self_id,component), ...):
        """

        def wrapper(f):
            # if first argument of function is named 'wrap', then inject in the call a wrapper with
            # lambda elem: class.wrap(self_id, elem)
            if next(iter(inspect.signature(f).parameters)) == "wrap":
                # callback start with the magic 'wrap' argument
                # register with an extra State("self","id")
                # a new callback that calls the original callback
                def my_callback_wrapper(**kwargs):
                    self_id = kwargs.pop("self_id")
                    return f(
                        wrap=lambda component, self_id=self_id: wrap(self_id, component), **kwargs
                    )

                self._app.callback(*args, State("self", "id"))(my_callback_wrapper)
            else:
                result = self._app.callback(*args)(f)

            return result

        return wrapper


class DependencyUnmatched(Exception):
    pass


class Alias(dd.DashDependency):
    pass


class ComposedComponentTransform(DashTransform):
    """Rewrite callback dependencies for composed components"""

    TYPE_NAME = "composed_type"

    def register_composed_component(self, composed_component_class):
        if isinstance(self._explicit_composed_components, ComposedComponentMixin):
            # component is an instance, register the class
            composed_component_class = composed_component_class.__class__

        self._explicit_composed_components.append(composed_component_class)

    def __init__(self, app):
        # keep reference to the Dash app
        self._app = app

        # list of explicitly registered composed components
        self._explicit_composed_components = []

        # store (__class__, generic_key) of composed components already declared
        self._callbacks_declared = set()

        # store (__class__, generic_key) -> callbacks of composed components already declared
        self._callbacks_declared_list = defaultdict(list)

        # create lock to manipulate self._callbacks_declared
        self._callbacks_declared_lock = threading.Lock()

    def is_component_already_registered(
            self, composed_component: ComposedComponentMixin, mark_as_registered=False
    ):
        with self._callbacks_declared_lock:
            # check if declare_callbacks already declared with the given compo id structure (if so, skip the component)
            assert isinstance(composed_component.id, dict)

            key = composed_component.get_generic_key()
            if key in self._callbacks_declared:
                logger.info(
                    f"callbacks already declared for {key}"
                )
                return True

            if mark_as_registered:
                logger.info(
                    f"declaring callbacks for {key}"
                )
                # mark the type as being already declared
                self._callbacks_declared.add(key)
                return False

        # we should not be here as only call with mark_as_registered=False with dynamic components
        logger.error(
            f"no callbacks declared for {composed_component.__class__.__qualname__}.{normalized_id}"
        )
        return False

    def get_newly_registered_callbacks(self, composed_component: ComposedComponentMixin):
        """Return a list of the newly registered declare_callbacks for the given composed_component.

        Return an empty list if the declare_callbacks for the composed_component have already
        been registered"""
        # check if the component is already registered and if so skip it
        # and otherwise mark it as registered
        if self.is_component_already_registered(composed_component, mark_as_registered=True):
            return []

        callbacks = self._app.callbacks

        # store the length of the declare_callbacks list to be able to detect afterwards which declare_callbacks have been added
        n = len(callbacks)

        # call the ComposedComponent `declare_callbacks` that will add to the cc its own declare_callbacks
        composed_component._app = self._app
        composed_component.declare_callbacks()

        logger.info(
            f"{len(callbacks) - n} new callbacks for {composed_component.get_generic_key()}"
        )

        self._callbacks_declared_list[composed_component.get_generic_key()] = callbacks[n:]

        return callbacks[n:]

    def _specialise_dependency(self, dependency, components):
        """Take a dependency and a list of component contexts and adapt the dependency to be aligned
        to one of the component:

        The component context can be:
        - a component (._original and .id) are used for the adaptation (as component)
        - a tuple (original dependency, final dependency) for aliases

        If dependency contains Wilcards (ALL, MATCH, ...) they are kept in the transformation.
        """
        for child in components:
            if isinstance(child, Component):
                if not hasattr(child, "_original_id"):
                    # skip as component without _original_id
                    continue

                if dependency == dd.DashDependency(
                        child._original_id, dependency.component_property
                ):
                    # found the children the dependency is referring to
                    dependency.component_id = new_id = {
                        **child.id,
                        **_wrap_child_id(
                            parent_id=child.parent_composed_component.id,
                            child_id=dependency.component_id,
                            match_parent=True,
                        ),
                    }
                    return
            else:
                (dep_alias, dep_alias_original, dep_aliased) = child
                if dep_alias_original == dependency:
                    dependency.component_id = dep_aliased.component_id
                    dependency.component_property = dep_aliased.component_property
                    return
        else:
            raise DependencyUnmatched(f"Could not match {dependency} with any of the {components}")

    def _register_callbacks(
            self, composed_component: ComposedComponentMixin
    ):
        # get new declare_callbacks registered for a given comp
        self.get_newly_registered_callbacks(composed_component)

    def _process_composedcomponent_internal_callbacks(
            self, key, callbacks
    ):
        """For each composed component present in the layout at the start of the application,
        trigger the callback declaration (once per class of composed component and structure of id)
        and rewrite the dependencies of the callback (that can only refers to children elements)."""

        logger.info(f"handle internal callbacks for {key}")

        ComposedComponent, composed_component_generic_id_frozen = key
        composed_component_generic_id = dict(composed_component_generic_id_frozen)
        # for each composed component, register the declare_callbacks and postprocess their args
        assert issubclass(ComposedComponent, ComposedComponentMixin)

        # for each internal callback, all ids of internal components should be childified through the GENERIC parent
        # as well as 'self'
        for callback in callbacks:
            logger.debug(f"handling callback {callback['f'].__qualname__} for {composed_component_generic_id}")
            for dependency in callback["sorted_args"]:
                dependency_before = copy(dependency)
                if dependency == Output("self", "children") and ComposedComponent._properties:
                    raise ValueError(
                        f"You are using {dependency} of {ComposedComponent} which"
                        f" has properties {ComposedComponent._properties}.\n"
                        f"This is not allowed as the properties have been dynamically added"
                        f" at the end of the {dependency} and you may loose them.\n"
                        f"Use instead an internal Div.children to do what you want."
                    )
                elif dependency.component_id == "self":
                    # handle the self
                    dependency.component_id = composed_component_generic_id
                else:
                    # handle references to children ids
                    self._specialise_dependency(
                        dependency, composed_component.children_composed_component
                    )
                logger.debug(f"converted {dependency_before} to {dependency}")
            print("after", callback)

    def _get_composed_components_with_ids(self, layout):
        # get all components of the layout that are ComposedComponentMixin
        # as well as the explicitly declared ComposedComponentMixin
        composed_components_with_ids = [
                                           comp for comp in layout._traverse_ids() if
                                           isinstance(comp, ComposedComponentMixin)
                                       ] + self._explicit_composed_components

        # add the cc/root layout itself if it is a ComposedComponentMixin
        if isinstance(layout, ComposedComponentMixin) and layout.id:
            composed_components_with_ids.append(layout)

        return composed_components_with_ids

    def apply(self, callbacks):
        """Add declare_callbacks from composed elements found in cc.layout or
        registered explicitly via `register_composed_component`.
        """

        logging.debug("starting 'apply' phase")

        composed_components_with_ids = self._get_composed_components_with_ids(self._app.layout)

        ## rewrite/adapt ids of children elements
        # this should also be done when components are added dynamically
        logging.debug("rewriting ids of composed components")
        for c in composed_components_with_ids:
            # start recursive process on ComposedComponentMixins with no parent (ie root elements)
            if isinstance(c, ComposedComponentMixin) and not hasattr(
                    c, "parent_composed_component"
            ):
                _rewrite_children_ids(c)

        ## declare callbacks from composed components
        for composed_component in composed_components_with_ids:
            self._register_callbacks(composed_component)

        # rewrite dependencies of all internal declare_callbacks added by composed components
        # to resolve them to generic ids
        for key, callbacks in self._callbacks_declared_list.items():
            self._process_composedcomponent_internal_callbacks(key, callbacks)

        ## process all declare_callbacks
        # replace ids
        self._process_standard_callbacks_replace_ids(self._app.layout, self._app.callbacks)
        # replace aliases
        self._process_standard_callbacks_replace_aliases(self._app.layout, self._app.callbacks)

        print(yaml.dump(self._app.callbacks_to_yaml(), sort_keys=False))
        print(yaml.dump(self._app.layout_to_yaml(), sort_keys=False))

        return callbacks

    def _process_standard_callbacks_replace_aliases(self, layout, callbacks):
        """Replace aliases to composed components in declare_callbacks."""

        # get all component with id changed (ie with an _original_id) that are not embedded in another component
        def unroll_aliases(cc: ComposedComponentMixin):
            """Get aliases for children composed components + interpret current aliases """
            result = []
            assert isinstance(cc, ComposedComponentMixin)

            for c in cc.children_composed_component:
                if not isinstance(c, ComposedComponentMixin):
                    continue
                children_aliases = unroll_aliases(c)
                # for (dep_original, dep_final) in children_aliases:
                #     dep_original.component_id =_wrap_child_id(c.id, dep_original.component_id)
                #     dep_final.component_id = _wrap_child_id(c.id, dep_final.component_id)

                result.extend(children_aliases)

            self_aliases = []
            for prop, dep in cc._aliases.items():
                # TODO: see if 'self' should be renamed in process to allow match with previous aliases
                if dep.component_id == "self":
                    dep = dd.DashDependency(cc._original_id, dep.component_property)
                    try:
                        # try to match against children aliases
                        self._specialise_dependency(dep, self_aliases)
                    except DependencyUnmatched:
                        pass
                else:
                    try:
                        # match against direct children
                        self._specialise_dependency(dep, cc.children_composed_component)
                    except DependencyUnmatched:
                        raise ValueError(
                            f"Could not resolve alias {cc.__class__.__qualname__}.{prop}.\n"
                            f"Check that {dep} exists."
                        )

                alias_resolution = (
                    # add fully resolve alias dependency
                    dd.DashDependency(cc.id, prop),
                    # add local alias dependency
                    dd.DashDependency(cc._original_id, prop),
                    # add fully resolved aliased dependency, binded to cc (for MATCH)
                    dd.DashDependency({**dep.component_id, **cc.id}, dep.component_property),
                )
                self_aliases.append(alias_resolution)
                result.append(alias_resolution)

            return result

        map_alias2final = [
            alias
            for c in layout._traverse_ids()
            if (
                    hasattr(c, "_original_id")  # id changed
                    and not hasattr(c, "parent_composed_component")  # connected to root layout
            )
            for alias in unroll_aliases(c)
        ]

        for callback in callbacks:
            for dependency in callback["sorted_args"]:
                # look if an alias is found
                for (dep_alias, dep_alias_original, dep_aliased) in map_alias2final:
                    # for original_id, final in map_alias2final:
                    if dep_alias == dependency:
                        dependency.component_id = {
                            **dep_aliased.component_id,
                            **dependency.component_id,
                        }
                        dependency.component_property = dep_aliased.component_property
                        break
                else:
                    assert "not found"

    def _process_standard_callbacks_replace_ids(self, layout, callbacks):
        """Replace original ids with final ids in declare_callbacks."""

        # get all component with id changed (ie with an _original_id) that are not embedded in another component
        map_original2final = [
            (c._original_id, c)
            for c in layout._traverse_ids()
            if (
                    hasattr(c, "_original_id")  # id changed
                    and not hasattr(c, "parent_composed_component")  # connected to root layout
            )
        ]

        for callback in callbacks:
            for dependency in callback["sorted_args"]:
                # look if dependency id has been rewritten
                for original_id, final in map_original2final:
                    if dd.DashDependency(original_id, dependency.component_property) == dependency:
                        # found mapping
                        print("---", dependency, original_id, final.id)
                        new_id = final.id.copy()

                        # overwrite any matchable part of the id
                        if isinstance(dependency.component_id, str):
                            new_id.update(id=dependency.component_id)
                        else:
                            new_id.update(dependency.component_id)

                        dependency.component_id = new_id

                        break
                else:
                    # dependency does not depend on a rewritten id component
                    print("xxx no need to rewrite", dependency)
            print(callback)

# endregion
