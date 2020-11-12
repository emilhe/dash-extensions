from dash.dependencies import MATCH, ALL
from dash_html_components import Div, Label

from dash_extensions.enrich import Dash
from dash_extensions.enrich_composed import (
    _find_simple_children_with_ids,
    ComponentScope,
    _make_id_generic,
    TYPE_NAME,
    _wrap_child_id,
    get_root_component,
    _hash_id,
    _get_conform_id,
    DashIdError,
)
from tests.composed_layouts import *


def test_make_generic():
    assert _make_id_generic({"id": "p"}) == {"id": MATCH}

    assert _make_id_generic({"id": ALL}) == {"id": ALL}

    assert _make_id_generic({"id": ALL, TYPE_NAME: "not-changed"}) == {
        "id": ALL,
        TYPE_NAME: "not-changed",
    }


def test_wrap_id():
    assert _wrap_child_id(parent_id={"id": "p"}, child_id="c") == {"*id": "c", "id": "p"}

    assert _wrap_child_id(parent_id={"id": "p"}, child_id="c", match_parent=True) == {
        "*id": "c",
        "id": MATCH,
    }

    assert _wrap_child_id(
        parent_id={"id": "p"}, child_id={"index": "c", "type": "test"}, match_parent=True
    ) == {"*index": "c", "*type": "test", "id": MATCH}

    assert _wrap_child_id(
        parent_id=_wrap_child_id(
            parent_id={"id": ALL}, child_id={"index": "c", "type": "test"}, match_parent=True
        ),
        child_id="foo",
    ) == {"**id": "foo", "*index": "c", "*type": "test", "id": ALL}

    assert _wrap_child_id(
        parent_id=_wrap_child_id(
            parent_id={"id": "p"}, child_id={"index": "c", "type": "test"}, match_parent=True
        ),
        child_id="foo",
        match_parent=True,
    ) == {"**id": "foo", "*index": MATCH, "*type": MATCH, "id": MATCH}

    assert _wrap_child_id(
        parent_id=_wrap_child_id(parent_id={"id": "p"}, child_id={"index": ALL, "type": "test"}),
        child_id="foo",
        match_parent=True,
    ) == {"**id": "foo", "*index": ALL, "*type": MATCH, "id": MATCH}


def test_find_simple_children_with_ids(layout_tree):
    l = list(_find_simple_children_with_ids(layout_tree))
    assert str(l) == str(
        [
            Div(
                children=[
                    Label("hello"),
                    Label(id="my-label"),
                    Label(id={"index": "my-matchable-label"}),
                ],
                id="my-a-div",
            ),
            Label(id="my-label"),
            Label(id={"index": "my-matchable-label"}),
            B(id="my-b"),
            C(id="my-c"),
            C(id="my-c-recursive"),
        ]
    )


def dump_callbacks(cbs):
    return [
        {"function": cb["f"].__qualname__, "dependencies": [str(dep) for dep in cb["sorted_args"]]}
        for cb in cbs
    ]


@pytest.fixture(scope="class")
def root_cc(request):
    request.cls.app = app = Dash()
    app.layout = html.Div(
        [
            F(id="my-base-f", conditional_flag=True),
            html.Div(),
            html.Div(id="foo", children=html.Div(id="foo-child")),
            html.Div(id={"_id": "baz"}),
        ]
    )

    @app.callback(Input("my-base-f", "memory"), Input("foo", "children"))
    def my_callback():
        return

    request.cls.root_callbacks = [my_callback]
    # create wrapper root component (html.Div with the app.layout as children)
    request.cls.root_cc = get_root_component(app.layout, request.cls.root_callbacks)


@pytest.mark.usefixtures("root_cc")
class TestComposedComponentApplyParts:
    def test_get_root_component(self):
        root_cc = self.root_cc
        assert root_cc.id == "root"
        assert root_cc.declare_callbacks() == self.root_callbacks
        assert root_cc.layout() == self.app.layout
        assert isinstance(root_cc, html.Div)
        assert isinstance(root_cc, ComposedComponentMixin)
        assert root_cc.children == [self.app.layout]
        assert root_cc._properties == []
        assert root_cc._aliases == {}

        self.root_cc = root_cc

    def test_create_from_cc(self):
        root_scope = ComponentScope.create_from_cc(None, self.root_cc)
        assert isinstance(root_scope, ComponentScope)

        assert root_scope._cc_class == self.root_cc.__class__
        assert [id for id, _ in root_scope._children_ids] == [
            "my-base-f",
            "foo",
            "foo-child",
            {"_id": MATCH},
        ]
        assert root_scope.map_local_id_to_scope("my-base-f") == (
            "my-base-f",
            root_scope._children_ids[0][1],
        )
        assert root_scope._aliases_resolved == {}
        assert root_scope._generic_key == {}
        assert root_scope._map_childid_to_fullid["my-base-f"]({}, "c") == {"class": "F", "id": "c"}
        assert root_scope._map_local_to_generic["my-base-f"]("p") == {"class": "F", "id": "p"}
        assert (
            root_scope._children_ids[0][1]
            == root_scope._children_scopes[_hash_id({"id": MATCH, "class": "F"})]
        )
        child_scope = root_scope._children_ids[0][1]
        assert isinstance(child_scope, ComponentScope)
        assert child_scope._aliases_resolved == {
            "memory": Alias("memory", "data"),
            "value": Alias("label", "children"),
        }
        assert child_scope._generic_key == {"class": "F", "id": MATCH}
        assert child_scope._map_childid_to_fullid["my-recursive-f"]({}, "c") == {
            "class": "F",
            "id": "c",
        }
        assert child_scope._map_local_to_generic["my-recursive-f"]("p") == {
            "*class": "F",
            "*id": "p",
            "class": "F",
            "id": MATCH,
        }

        assert child_scope.map_local_id("self") == {"class": "F", "id": MATCH}
        assert child_scope.map_local_id("my-recursive-f") == {
            "*class": "F",
            "*id": "my-recursive-f",
            "class": "F",
            "id": MATCH,
        }
        assert child_scope.map_local_id("label") == {"*id": "label", "class": "F", "id": MATCH}
        with pytest.raises(
            DashIdError, match="Could not find scope related to id 'not-existing-label'"
        ):
            child_scope.map_local_id("not-existing-label")

    def test_register_callbacks(self):
        self.root_scope = root_scope = ComponentScope.create_from_cc(None, self.root_cc)
        root_scope.register_callbacks(callback_decorator=self.app.callback)
        child_scope = root_scope._children_ids[0][1]

        assert root_scope.callbacks == self.root_callbacks

        # check callback signature before rewriting callback dependencies
        assert repr(root_scope.callbacks[0]["sorted_args"]) == repr(
            [Input("my-base-f", "memory"), Input("foo", "children")]
        )
        assert repr(child_scope.callbacks[0]["sorted_args"]) == repr(
            [Input("self", "value"), State("label", "children"), Output("self", "memory")]
        )

        # rewrite callback dependencies
        root_scope.rewrite_callback_dependencies()

        # check callback signature after rewriting callback dependencies
        assert repr(root_scope.callbacks[0]["sorted_args"]) == repr(
            [
                Input({"*id": "memory", "class": "F", "id": "my-base-f"}, "data"),
                Input("foo", "children"),
            ]
        )
        assert repr(child_scope.callbacks[0]["sorted_args"]) == repr(
            [
                Input({"*id": "label", "class": "F", "id": MATCH}, "children"),
                State({"*id": "label", "class": "F", "id": MATCH}, "children"),
                Output({"*id": "memory", "class": "F", "id": MATCH}, "data"),
            ]
        )

        # check ids of components before adaptation
        assert [comp.id for comp in self.root_cc._traverse_ids()] == [
            "my-base-f",
            "label",
            "memory",
            "my-recursive-f",
            "label",
            "memory",
            "foo",
            "foo-child",
            {"_id": "baz"},
        ]

        root_scope.adapt_ids(component=self.root_cc)

        # check ids of components after adaptation
        assert [comp.id for comp in self.root_cc._traverse_ids()] == [
            {"class": "F", "id": "my-base-f"},
            {"*id": "label", "class": "F", "id": "my-base-f"},
            {"*id": "memory", "class": "F", "id": "my-base-f"},
            {"*id": "my-recursive-f", "*class": "F", "class": "F", "id": "my-base-f"},
            {
                "**id": "label",
                "*id": "my-recursive-f",
                "*class": "F",
                "class": "F",
                "id": "my-base-f",
            },
            {
                "**id": "memory",
                "*id": "my-recursive-f",
                "*class": "F",
                "class": "F",
                "id": "my-base-f",
            },
            "foo",
            "foo-child",
            {"_id": "baz"},
        ]


class TestComposedComponentApplyIntegration:
    def test_apply(self):
        app = Dash()
        app.layout = html.Div(
            [
                F(id="my-base-f", conditional_flag=True),
                html.Div(),
                html.Div(id="foo", children=html.Div(id="foo-child")),
                html.Div(id={"_id": "baz"}),
            ]
        )

        @app.callback(Input("my-base-f", "memory"), Input("foo", "children"))
        def my_callback():
            return

        app._setup_server()

        assert app._composed_component_transform.find_scope_for_id(
            {"id": "my-base-f", "class": "F"}
        )._generic_key == {"class": "F", "id": MATCH}
        assert app._composed_component_transform.find_scope_for_id(
            {"*id": "baz", "*class": "F", "id": "foo", "class": "F"}
        )._generic_key == {"*id": MATCH, "*class": "F", "id": MATCH, "class": "F"}

        with pytest.raises(DashIdError):
            app._composed_component_transform.find_scope_for_id(
                {"*id": "baz", "*class": "B", "id": "foo", "class": "F"}
            )


def test_composed_component_properties_aliases():
    class A(ComposedComponentMixin, html.Div):
        _aliases = "foo"

    # need 'id'
    with pytest.raises(TypeError, match="missing 1 required keyword-only argument: 'id'"):
        A()

    # wrong _aliases
    with pytest.raises(ValueError, match="should be a dict "):
        A(id="foo")

    class A(ComposedComponentMixin, html.Div):
        _aliases = {"my-prop": Input("my-slider", "value")}

    # wrong _aliases
    with pytest.raises(ValueError, match="should be a dict "):
        A(id="foo")

    class A(ComposedComponentMixin, html.Div):
        _aliases = {"my-prop": Alias("my-slider", "value")}

    # _aliases OK
    A(id="foo")

    class A(ComposedComponentMixin, html.Div):
        _properties = ["my-prop"]
        _aliases = {"my-prop": Alias("my-slider", "value")}

    # _aliases & _properties OK
    with pytest.raises(ValueError, match="have the same name as some aliased properties "):
        A(id="foo")

    class A(ComposedComponentMixin, html.Div):
        _properties = ["my-prop"]
        _aliases = {"my-aliased-prop": Alias("my-slider", "value")}

    # _aliases & _properties OK
    A(id="foo")

    # test default methods
    assert A.declare_callbacks() is None
    assert A(id="foo").layout() == []
    assert A(id="foo").register_components_explicitly() == []


def test_get_conform_id():
    class A(ComposedComponentMixin, html.Div):
        pass

    assert _get_conform_id(A, "foo") == {"class": "test_get_conform_id.<locals>.A", "id": "foo"}
    assert _get_conform_id(A(id="foo")) == {"class": "test_get_conform_id.<locals>.A", "id": "foo"}
    assert _get_conform_id(A(id={"type": "A", "index": "foo"})) == {
        "class": "test_get_conform_id.<locals>.A",
        "index": "foo",
        "type": "A",
    }

    with pytest.raises(
        ValueError,
        match="You should call with either a composed component class "
        "and an id or just a component instance",
    ):
        _get_conform_id(A(id="foo"), "foo")


def test_composed_component_siblings():
    class A(ComposedComponentMixin, html.Div):
        pass

    class B(ComposedComponentMixin, html.Div):
        def __init__(self, id, has_a):
            super().__init__(id=id, layout_kwargs=dict(has_a=has_a))

        def layout(self, has_a):
            if has_a:
                return [A(id="internal-a")]
            else:
                return []

    app = Dash()
    app.layout = html.Div(
        [
            A(id="a1"),
            B(id="b1", has_a=False),
            B(id="b2", has_a=True),
            A(id="a2"),
            A(id={"index": "a3"}),
        ]
    )
    app._setup_server()

    assert len(app._composed_component_transform._root_scope._children_ids) == 5
    # scope for similar id structure and class should be merged
    assert len(app._composed_component_transform._root_scope._children_scopes) == 3


def test_resolve_dependency():
    class A(ComposedComponentMixin, html.Div):
        _aliases = {"value": Alias("label1", "children")}

        def layout(self, **kwargs):
            return [
                B(id="label1"),
                B(id={"type": "special", "index": "sublabel1"}),
                B(id={"type": "special", "index": "sublabel2"}),
                html.Label(id="label2"),
            ]

        @classmethod
        def declare_callbacks(cls):
            @cls.callback(
                Input({"type": "special", "index": ALL}, "value"), Output("label1", "children")
            )
            def cc_callback(special_labels):
                return special_labels

    class B(ComposedComponentMixin, html.Div):
        _aliases = {"value": Alias("btn", "nclicks")}

        def layout(self, **kwargs):
            return [html.Button(id="btn")]

    app = Dash()
    app.layout = html.Div([A(id="a1")])

    @app.callback(Input("a1", "value"), Output("a1", "children"))
    def main_callback(label1):
        return

    app._setup_server()

    assert app.callbacks_to_yaml() == [
        {
            "function": "test_resolve_dependency.<locals>.main_callback",
            "inputs": [
                '{"*class":"test_resolve_dependency.<locals>.B","*id":"label1","class":"test_resolve_dependency.<locals>.A","id":"a1"}.children'
            ],
            "outputs": ['{"class":"test_resolve_dependency.<locals>.A","id":"a1"}.children'],
        },
        {
            "function": "test_resolve_dependency.<locals>.A.declare_callbacks.<locals>.cc_callback",
            "inputs": [
                '{"**id":"btn","*class":"test_resolve_dependency.<locals>.B","*index":["ALL"],"*type":"special","class":"test_resolve_dependency.<locals>.A","id":["MATCH"]}.nclicks'
            ],
            "outputs": [
                '{"*class":"test_resolve_dependency.<locals>.B","*id":"label1","class":"test_resolve_dependency.<locals>.A","id":["MATCH"]}.children'
            ],
        },
    ]


def test_all_variants():
    # test all variants of component names and callbacks dependencies
    _ids = ["my-id-simple", {"my-class": "my-class-index"}, {"id": "my-id-structured"}]
    _aliases = {
        "my-alias-cc-simple": Alias("my-id-simple", "my-value"),
        "my-alias-cc-structured": Alias({"my-class": "my-class-index"}, "my-value"),
        "my-alias-simple": Alias("label-my-id-simple", "children"),
        "my-alias-structured": Alias({"my-class": "my-class-index", "is-label": True}, "children"),
    }

    def ids(text):
        return [
            f"{text}-{_id}" if isinstance(_id, str) else {f"{text}-{k}": v for k, v in _id.items()}
            for _id in _ids
        ]

    def aliases(text):
        return {
            **{f"my-alias-cc-{i}": Alias(_id, "my-value") for i, _id in enumerate(ids(text))},
            **{
                f"my-alias-{i}": Alias(_id, "children")
                for i, _id in enumerate(ids(f"label-{text}"))
            },
        }

    class A(ComposedComponentMixin, html.Div):
        _properties = ["my-state"]
        _aliases = aliases("a")

        def layout(self, **kwargs):
            return [B(id=id) for id in ids("a")] + [html.Label(id=id) for id in ids("label-a")]

        @classmethod
        def declare_callbacks(cls):
            @cls.callback(
                *(
                    # add input on all children on ids
                    [Input(component_id=id, component_property="children") for id in ids("a")]
                    +
                    # add state on all aliased properties
                    [
                        State(component_id="self", component_property=prop)
                        for prop in aliases("a").keys()
                    ]
                    +
                    # add state + output with MATCH
                    [
                        State(component_id={k: MATCH for k in id}, component_property="my-value")
                        for id in ids("a")
                        if isinstance(id, dict)
                    ]
                    + [
                        Output(component_id={k: MATCH for k in id}, component_property="my-value")
                        for id in ids("a")
                        if isinstance(id, dict)
                    ]
                    +
                    # add state with ALL
                    [
                        State(component_id={k: ALL for k in id}, component_property="my-value")
                        for id in ids("a")
                        if isinstance(id, dict)
                    ]
                    +
                    # add state with ALL
                    [
                        State(component_id="self", component_property=prop)
                        for prop in aliases("a").keys()
                    ]
                )
            )
            def a_callback():
                pass

    class B(ComposedComponentMixin, html.Div):
        _aliases = {"my-value": Alias("self", "children")}

        @classmethod
        def declare_callbacks(cls):
            @cls.callback(Input("self", "my-value"), Output("self", "children"))
            def b_callback():
                pass

    A.__qualname__ = "A"
    B.__qualname__ = "B"

    app = Dash()
    app.layout = html.Div([A(id=id) for id in ids("core")])
    app._setup_server()
    assert app.callbacks_to_yaml() == [
        {
            "function": "test_all_variants.<locals>.A.declare_callbacks.<locals>.a_callback",
            "inputs": [
                '{"*class":"B","*id":"a-my-id-simple","class":"A","id":["MATCH"]}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","id":["MATCH"]}.children',
            ],
            "outputs": [
                '{"*a-my-class":["MATCH"],"*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*a-id":["MATCH"],"*class":"B","class":"A","id":["MATCH"]}.children',
            ],
            "states": [
                '{"*class":"B","*id":"a-my-id-simple","class":"A","id":["MATCH"]}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*id":"label-a-my-id-simple","class":"A","id":["MATCH"]}.children',
                '{"*label-a-my-class":"my-class-index","class":"A","id":["MATCH"]}.children',
                '{"*label-a-id":"my-id-structured","class":"A","id":["MATCH"]}.children',
                '{"*a-my-class":["MATCH"],"*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*a-id":["MATCH"],"*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*a-my-class":["ALL"],"*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*a-id":["ALL"],"*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*class":"B","*id":"a-my-id-simple","class":"A","id":["MATCH"]}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","id":["MATCH"]}.children',
                '{"*id":"label-a-my-id-simple","class":"A","id":["MATCH"]}.children',
                '{"*label-a-my-class":"my-class-index","class":"A","id":["MATCH"]}.children',
                '{"*label-a-id":"my-id-structured","class":"A","id":["MATCH"]}.children',
            ],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": ['{"*class":"B","*id":["MATCH"],"class":"A","id":["MATCH"]}.children'],
            "outputs": ['{"*class":"B","*id":["MATCH"],"class":"A","id":["MATCH"]}.children'],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": [
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","id":["MATCH"]}.children'
            ],
            "outputs": [
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","id":["MATCH"]}.children'
            ],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": ['{"*a-id":["MATCH"],"*class":"B","class":"A","id":["MATCH"]}.children'],
            "outputs": ['{"*a-id":["MATCH"],"*class":"B","class":"A","id":["MATCH"]}.children'],
        },
        {
            "function": "test_all_variants.<locals>.A.declare_callbacks.<locals>.a_callback",
            "inputs": [
                '{"*class":"B","*id":"a-my-id-simple","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","core-my-class":"my-class-index"}.children',
            ],
            "outputs": [
                '{"*a-my-class":["MATCH"],"*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-id":["MATCH"],"*class":"B","class":"A","core-my-class":"my-class-index"}.children',
            ],
            "states": [
                '{"*class":"B","*id":"a-my-id-simple","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*id":"label-a-my-id-simple","class":"A","core-my-class":"my-class-index"}.children',
                '{"*label-a-my-class":"my-class-index","class":"A","core-my-class":"my-class-index"}.children',
                '{"*label-a-id":"my-id-structured","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-my-class":["MATCH"],"*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-id":["MATCH"],"*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-my-class":["ALL"],"*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-id":["ALL"],"*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*class":"B","*id":"a-my-id-simple","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","core-my-class":"my-class-index"}.children',
                '{"*id":"label-a-my-id-simple","class":"A","core-my-class":"my-class-index"}.children',
                '{"*label-a-my-class":"my-class-index","class":"A","core-my-class":"my-class-index"}.children',
                '{"*label-a-id":"my-id-structured","class":"A","core-my-class":"my-class-index"}.children',
            ],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": [
                '{"*class":"B","*id":["MATCH"],"class":"A","core-my-class":"my-class-index"}.children'
            ],
            "outputs": [
                '{"*class":"B","*id":["MATCH"],"class":"A","core-my-class":"my-class-index"}.children'
            ],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": [
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-my-class":"my-class-index"}.children'
            ],
            "outputs": [
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-my-class":"my-class-index"}.children'
            ],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": [
                '{"*a-id":["MATCH"],"*class":"B","class":"A","core-my-class":"my-class-index"}.children'
            ],
            "outputs": [
                '{"*a-id":["MATCH"],"*class":"B","class":"A","core-my-class":"my-class-index"}.children'
            ],
        },
        {
            "function": "test_all_variants.<locals>.A.declare_callbacks.<locals>.a_callback",
            "inputs": [
                '{"*class":"B","*id":"a-my-id-simple","class":"A","core-id":["MATCH"]}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","core-id":["MATCH"]}.children',
            ],
            "outputs": [
                '{"*a-my-class":["MATCH"],"*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*a-id":["MATCH"],"*class":"B","class":"A","core-id":["MATCH"]}.children',
            ],
            "states": [
                '{"*class":"B","*id":"a-my-id-simple","class":"A","core-id":["MATCH"]}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*id":"label-a-my-id-simple","class":"A","core-id":["MATCH"]}.children',
                '{"*label-a-my-class":"my-class-index","class":"A","core-id":["MATCH"]}.children',
                '{"*label-a-id":"my-id-structured","class":"A","core-id":["MATCH"]}.children',
                '{"*a-my-class":["MATCH"],"*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*a-id":["MATCH"],"*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*a-my-class":["ALL"],"*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*a-id":["ALL"],"*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*class":"B","*id":"a-my-id-simple","class":"A","core-id":["MATCH"]}.children',
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*a-id":"my-id-structured","*class":"B","class":"A","core-id":["MATCH"]}.children',
                '{"*id":"label-a-my-id-simple","class":"A","core-id":["MATCH"]}.children',
                '{"*label-a-my-class":"my-class-index","class":"A","core-id":["MATCH"]}.children',
                '{"*label-a-id":"my-id-structured","class":"A","core-id":["MATCH"]}.children',
            ],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": ['{"*class":"B","*id":["MATCH"],"class":"A","core-id":["MATCH"]}.children'],
            "outputs": ['{"*class":"B","*id":["MATCH"],"class":"A","core-id":["MATCH"]}.children'],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": [
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-id":["MATCH"]}.children'
            ],
            "outputs": [
                '{"*a-my-class":"my-class-index","*class":"B","class":"A","core-id":["MATCH"]}.children'
            ],
        },
        {
            "function": "test_all_variants.<locals>.B.declare_callbacks.<locals>.b_callback",
            "inputs": ['{"*a-id":["MATCH"],"*class":"B","class":"A","core-id":["MATCH"]}.children'],
            "outputs": [
                '{"*a-id":["MATCH"],"*class":"B","class":"A","core-id":["MATCH"]}.children'
            ],
        },
    ]
