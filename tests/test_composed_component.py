import dash_html_components as html
import pytest
import yaml
from dash.dependencies import ALL, MATCH

from enrich import Dash, Output, Input, State
from enrich_composed import ComposedComponentMixin, ComposedComponentTransform


@pytest.fixture
def layout_A_contains_B():
    class A(ComposedComponentMixin, html.Div):
        _composed_type = "A"

        def layout(self, **kwargs):
            return [
                B(id="component-b"),
                B(id={"type": "list", "id": "baz"}),
                B(id={"type": "list", "id": "foo"}),
                html.Div(id="direct-a"),
                html.Div(id={"index": "direct-a", "type": "foo"}),
            ]

        def declare_callbacks(cls, app):
            @app.callback(
                Input({"type": "list", "id": ALL}, "children"),
                Input("component-b", "memory"),
                Output("direct-a", "children"),
                Output("self", "children"),
            )
            def foo():
                pass

    class B(ComposedComponentMixin, html.Div):
        _composed_type = "B"
        _properties = ["memory"]

        def layout(self, **kwargs):
            return [html.Div(id="component-b", children=html.Div(id="component-b-a"))]

        def declare_callbacks(cls, app):
            @app.callback(Input("self", "memory"), Output("self", "children"))
            def memory2children():
                pass

    c = A(id="root")
    return c


def test_make_generic():
    assert ComposedComponentMixin._make_generic({"id": "p"}) == {"id": MATCH}

    assert ComposedComponentMixin._make_generic({"id": ALL}) == {"id": ALL}

    assert ComposedComponentMixin._make_generic(
        {"id": ALL, ComposedComponentTransform.TYPE_NAME: "not-changed"}
    ) == {"id": ALL, "composed_type": "not-changed"}


def test_wrap_child_id():
    assert ComposedComponentMixin._wrap_child_id(parent_id={"id": "p"}, child_id="c") == {
        "child_id": "c",
        "id": "p",
    }

    assert ComposedComponentMixin._wrap_child_id(
        parent_id={"id": "p"}, child_id="c", match_parent=True
    ) == {"child_id": "c", "id": MATCH}

    assert ComposedComponentMixin._wrap_child_id(
        parent_id={"id": "p"}, child_id={"index": "c", "type": "test"}, match_parent=True
    ) == {"child_index": "c", "child_type": "test", "id": MATCH}

    assert ComposedComponentMixin._wrap_child_id(
        parent_id=ComposedComponentMixin._wrap_child_id(
            parent_id={"id": ALL}, child_id={"index": "c", "type": "test"}, match_parent=True
        ),
        child_id="foo",
    ) == {"child_child_id": "foo", "child_index": "c", "child_type": "test", "id": ALL}

    assert ComposedComponentMixin._wrap_child_id(
        parent_id=ComposedComponentMixin._wrap_child_id(
            parent_id={"id": "p"}, child_id={"index": "c", "type": "test"}, match_parent=True
        ),
        child_id="foo",
        match_parent=True,
    ) == {"child_child_id": "foo", "child_index": MATCH, "child_type": MATCH, "id": MATCH}

    assert ComposedComponentMixin._wrap_child_id(
        parent_id=ComposedComponentMixin._wrap_child_id(
            parent_id={"id": "p"}, child_id={"index": ALL, "type": "test"}
        ),
        child_id="foo",
        match_parent=True,
    ) == {"child_child_id": "foo", "child_index": ALL, "child_type": MATCH, "id": MATCH}


def test_rewrite_id(layout_A_contains_B):
    cct = ComposedComponentTransform(None)

    cct._rewrite_children_ids([layout_A_contains_B])

    def dump_ids(c, tab=0):
        print(f"{'  ' * tab}{c.__class__.__name__:<6}id: {c.id}")
        result = [(c.__class__.__name__, c.id)]
        if isinstance(c, ComposedComponentMixin):
            for child in c.children_composed_component:
                result.append(dump_ids(child, tab + 2))
        return result

    assert dump_ids(layout_A_contains_B) == [
        ("A", {"composed_type": "A", "id": "root"}),
        [
            (
                "B",
                {
                    "child_composed_type": "B",
                    "child_id": "component-b",
                    "composed_type": "A",
                    "id": "root",
                },
            ),
            [
                (
                    "Div",
                    {
                        "child_child_id": "component-b",
                        "child_composed_type": "B",
                        "child_id": "component-b",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
            [
                (
                    "Div",
                    {
                        "child_child_id": "component-b-a",
                        "child_composed_type": "B",
                        "child_id": "component-b",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
            [
                (
                    "Store",
                    {
                        "child_child_id": "memory",
                        "child_composed_type": "B",
                        "child_id": "component-b",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
        ],
        [
            (
                "B",
                {
                    "child_composed_type": "B",
                    "child_id": "baz",
                    "child_type": "list",
                    "composed_type": "A",
                    "id": "root",
                },
            ),
            [
                (
                    "Div",
                    {
                        "child_child_id": "component-b",
                        "child_composed_type": "B",
                        "child_id": "baz",
                        "child_type": "list",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
            [
                (
                    "Div",
                    {
                        "child_child_id": "component-b-a",
                        "child_composed_type": "B",
                        "child_id": "baz",
                        "child_type": "list",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
            [
                (
                    "Store",
                    {
                        "child_child_id": "memory",
                        "child_composed_type": "B",
                        "child_id": "baz",
                        "child_type": "list",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
        ],
        [
            (
                "B",
                {
                    "child_composed_type": "B",
                    "child_id": "foo",
                    "child_type": "list",
                    "composed_type": "A",
                    "id": "root",
                },
            ),
            [
                (
                    "Div",
                    {
                        "child_child_id": "component-b",
                        "child_composed_type": "B",
                        "child_id": "foo",
                        "child_type": "list",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
            [
                (
                    "Div",
                    {
                        "child_child_id": "component-b-a",
                        "child_composed_type": "B",
                        "child_id": "foo",
                        "child_type": "list",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
            [
                (
                    "Store",
                    {
                        "child_child_id": "memory",
                        "child_composed_type": "B",
                        "child_id": "foo",
                        "child_type": "list",
                        "composed_type": "A",
                        "id": "root",
                    },
                )
            ],
        ],
        [("Div", {"child_id": "direct-a", "composed_type": "A", "id": "root"})],
        [
            (
                "Div",
                {
                    "child_index": "direct-a",
                    "child_type": "foo",
                    "composed_type": "A",
                    "id": "root",
                },
            )
        ],
    ]


def test_get_composed_components_with_ids(layout_A_contains_B):
    cct = ComposedComponentTransform(None)
    composed_components_with_ids = cct._get_composed_components_with_ids(layout_A_contains_B)
    assert {frozenset(comp.id.items()) for comp in composed_components_with_ids} == {
        frozenset({("composed_type", "B"), ("id", "component-b")}),
        frozenset({("type", "list"), ("composed_type", "B"), ("id", "baz")}),
        frozenset({("id", "root"), ("composed_type", "A")}),
        frozenset({("type", "list"), ("composed_type", "B"), ("id", "foo")}),
    }


def dump_cb(app):
    return {
        cb["f"].__name__: {
            tuple(sorted(dep.component_id.items())): dep.component_property
            for t in [Input, State, Output]
            for dep in cb[t]
        }
        for cb in app.declare_callbacks
    }


def test_rewrite_callbacks(layout_A_contains_B):
    app = Dash()
    cct = ComposedComponentTransform(app)

    cct._rewrite_children_ids([layout_A_contains_B])

    composed_components_with_ids = cct._get_composed_components_with_ids(layout_A_contains_B)

    cct._process_composedcomponent_internal_callbacks(composed_components_with_ids)

    # check which declare_callbacks signatures have been declared
    assert {(str(cls), sign) for cls, sign in cct._callbacks_declared} == {
        (
            "<class 'tests.test_composed_component.layout_A_contains_B.<locals>.A'>",
            ("id", "composed_type"),
        ),
        (
            "<class 'tests.test_composed_component.layout_A_contains_B.<locals>.B'>",
            ("child_id", "child_composed_type", "id", "composed_type"),
        ),
        (
            "<class 'tests.test_composed_component.layout_A_contains_B.<locals>.B'>",
            ("child_type", "child_id", "child_composed_type", "id", "composed_type"),
        ),
    }

    after = dump_cb(app)

    assert after == {
        "foo": {
            (
                ("child_id", ALL),
                ("child_type", "list"),
                ("composed_type", "A"),
                ("id", MATCH),
            ): "children",
            (("child_id", "component-b"), ("composed_type", "A"), ("id", MATCH)): "memory",
            (("child_id", "direct-a"), ("composed_type", "A"), ("id", MATCH)): "children",
            (("composed_type", "A"), ("id", MATCH)): "children",
        },
        "memory2children": {
            (
                ("child_composed_type", "B"),
                ("child_id", MATCH),
                ("child_type", MATCH),
                ("composed_type", "A"),
                ("id", MATCH),
            ): "children"
        },
    }


def test_cct_apply(layout_A_contains_B):
    app = Dash()
    app.layout = layout_A_contains_B
    cct = ComposedComponentTransform(app)
    callbacks = cct.apply(app.callbacks)

    # print(yaml.dump(cc.layout_to_yaml(),sort_keys=False))
    assert app.layout_to_yaml() == yaml.load(
        """
A(root):
  id: root
  composed_type: A
children:
- B(component-b):
    child_id: component-b
    child_composed_type: B
    id: root
    composed_type: A
  children:
  - Div(component-b):
      child_child_id: component-b
      child_id: component-b
      child_composed_type: B
      id: root
      composed_type: A
  - Store(memory):
      child_child_id: memory
      child_id: component-b
      child_composed_type: B
      id: root
      composed_type: A
- 'B({''type'': ''list'', ''id'': ''baz''})':
    child_type: list
    child_id: baz
    child_composed_type: B
    id: root
    composed_type: A
  children:
  - Div(component-b):
      child_child_id: component-b
      child_type: list
      child_id: baz
      child_composed_type: B
      id: root
      composed_type: A
  - Store(memory):
      child_child_id: memory
      child_type: list
      child_id: baz
      child_composed_type: B
      id: root
      composed_type: A
- 'B({''type'': ''list'', ''id'': ''foo''})':
    child_type: list
    child_id: foo
    child_composed_type: B
    id: root
    composed_type: A
  children:
  - Div(component-b):
      child_child_id: component-b
      child_type: list
      child_id: foo
      child_composed_type: B
      id: root
      composed_type: A
  - Store(memory):
      child_child_id: memory
      child_type: list
      child_id: foo
      child_composed_type: B
      id: root
      composed_type: A
- Div(direct-a):
    child_id: direct-a
    id: root
    composed_type: A
- 'Div({''index'': ''direct-a'', ''type'': ''foo''})':
    child_index: direct-a
    child_type: foo
    id: root
    composed_type: A
"""
    )
    print(yaml.dump(app.callbacks_to_yaml(), sort_keys=False))
    assert app.callbacks_to_yaml() == yaml.load("""
- function: layout_A_contains_B.<locals>.B.declare_callbacks.<locals>.memory2children
  inputs:
  - '{"child_composed_type":"B","child_id":["MATCH"],"composed_type":"A","id":["MATCH"]}.memory'
  outputs:
  - '{"child_composed_type":"B","child_id":["MATCH"],"composed_type":"A","id":["MATCH"]}.children'
- function: layout_A_contains_B.<locals>.B.declare_callbacks.<locals>.memory2children
  inputs:
  - '{"child_composed_type":"B","child_id":["MATCH"],"child_type":["MATCH"],"composed_type":"A","id":["MATCH"]}.memory'
  outputs:
  - '{"child_composed_type":"B","child_id":["MATCH"],"child_type":["MATCH"],"composed_type":"A","id":["MATCH"]}.children'
- function: layout_A_contains_B.<locals>.A.declare_callbacks.<locals>.foo
  inputs:
  - '{"child_id":["ALL"],"child_type":"list","composed_type":"A","id":["MATCH"]}.children'
  - '{"child_id":"component-b","composed_type":"A","id":["MATCH"]}.memory'
  outputs:
  - '{"child_id":"direct-a","composed_type":"A","id":["MATCH"]}.children'
  - '{"composed_type":"A","id":["MATCH"]}.children'
""")