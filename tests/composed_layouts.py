import dash_html_components as html
import pytest

from dash_extensions.enrich import Input, State, Output
from dash_extensions.enrich_composed import ComposedComponentMixin, Alias


## standard layout

class A(ComposedComponentMixin, html.Div):
    def layout(self, **kwargs):
        return [
            html.Div(
                [
                    html.Label("hello"),
                    html.Label(id="my-label"),
                    html.Label(id={"index": "my-matchable-label"}),
                ],
                id="my-a-div",
            ),
            B(id="my-b"),
            C(id="my-c"),
            C(id="my-c-recursive", conditional_flag=True),
        ]

    @classmethod
    def declare_callbacks(cls):
        @cls.callback(Input("self", "children"), )
        def a_update(foo):
            return foo


class B(ComposedComponentMixin, html.Div):
    def layout(self, **kwargs):
        return [C(id={"index": "my-matchable-c"}), C(id="my-c-from-b")]

    @classmethod
    def declare_callbacks(cls):
        @cls.callback(Input("my-c-from-b", "children"),
                      Input("self", "children"), )
        def b_update(foo):
            return foo


class C(ComposedComponentMixin, html.Div):
    def __init__(self, id, conditional_flag=False):
        super().__init__(id=id)

        if conditional_flag:
            self.children.append(C(id="my-recursive-c"))

    def layout(self, **kwargs):
        return [html.Label("hello")]


@pytest.fixture
def layout_tree():
    return A(id="root-id")


@pytest.fixture
def layout_tree_div():
    return html.Div(A(id="root-id"))


## standard layout

class D(ComposedComponentMixin, html.Div):
    def layout(self, **kwargs):
        return [
            html.Div(
                [
                    html.Label("hello"),
                    html.Label(id="my-label"),
                    html.Label(id={"index": "my-matchable-label"}),
                ],
                id="my-a-div",
            ),
            E(id="my-b"),
            F(id="my-c"),
            F(id="my-c-recursive", conditional_flag=True),
        ]

    @classmethod
    def declare_callbacks(cls):
        @cls.callback(Input("self", "children"), )
        def a_update(foo):
            return foo


class E(ComposedComponentMixin, html.Div):
    def layout(self, **kwargs):
        return [F(id={"index": "my-matchable-c"}), F(id="my-c-from-b")]

    @classmethod
    def declare_callbacks(cls):
        @cls.callback(Input("my-c-from-b", "children"),
                      Input("self", "children"), )
        def b_update(foo):
            return foo


class F(ComposedComponentMixin, html.Div):
    _properties = ["memory"]
    _aliases = {"value": Alias("label", "children")}

    def __init__(self, id, conditional_flag=False):
        super().__init__(id=id)

        if conditional_flag:
            self.children.append(F(id="my-recursive-f"))

    def layout(self, **kwargs):
        return [html.Label("hello", id="label", )]

    @classmethod
    def declare_callbacks(cls):
        @cls.callback(Input("self", "value"),
                      State("label", "children"),
                      Output("self", "memory")
                      )
        def update_memory(value, revalue):
            return value


@pytest.fixture
def simple_alias():
    return F(id="my-base-f")
