"""Example that shows how aliases are resolved even across children"""
import logging
import sys

import dash_core_components as dcc
import dash_html_components as html
import flask
from dash.dependencies import State, ALL

from dash_extensions.enrich import Dash, Output, Input
from enrich_composed import ComposedComponentMixin, Alias, logger

logger.setLevel(logging.DEBUG)
logger.propagate = False
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class A(ComposedComponentMixin, html.Div):
    """Exposes a single alias to its B child."""

    _aliases = {"alias-a": Alias("b", "alias-b"), "alias-c": Alias("c", "alias-c")}
    _composed_type = "a"

    def layout(self, **kwargs):
        return [B(id="b"), C(id="c")]

    def declare_callbacks(self):
        """Declare the declare_callbacks that will handle the update of the size and info properties."""
        pass


class B(ComposedComponentMixin, html.Div):
    """Exposes a single alias to its B child."""

    _aliases = {"alias-b": Alias({"index":"c"}, "alias-c")}
    _composed_type = "b"

    def layout(self, **kwargs):
        return [C(id={"index":"c"})]

    def declare_callbacks(self):
        """Declare the declare_callbacks that will handle the update of the size and info properties."""
        pass


class C(ComposedComponentMixin, html.Div):
    """Exposes a single alias to its B child."""

    _properties = ["memory"]
    _aliases = {
        "alias-c": Alias("self", "memory"),
        "alias-input": Alias("internal", "value"),
        "alias-of-alias": Alias("self", "alias-c"),
    }
    _composed_type = "c"

    def layout(self, **kwargs):
        return [
            dcc.Input(id="internal"),
            html.Label(id={"index": "one"}),
            html.Label(id={"index": "two"}),
        ]

    def declare_callbacks(self):
        """Declare the declare_callbacks that will handle the update of the size and info properties."""

        @self.callback(
            Input("self", "alias-input"),
            State("internal", "children"),
            State({"index": ALL}, "children"),
            Output("self", "memory"),
        )
        def sync_memory(input, children, indexes):
            print(input, children, indexes)
            if input=="a":
                flask.request.environ.get('werkzeug.server.shutdown')()
            return input

        # @self.callback(
        #     Input("self", "alias-input"),
        #     Output("self", "children"),
        # )
        # def should_raise_error(input):
        #     return input


app = Dash(
    __name__,
    title="Composed Component cc - aliases",
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
)

app.layout = html.Div([A(id="me"), html.Label(id="out")])


@app.callback(Input("me", "alias-a"), Input("me", "alias-c"), Output("out", "children"))
def test_id(input_from_c2b2a, input_from_c2a):
    return [html.Label(input_from_c2b2a), html.Label(input_from_c2a)]


if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_hot_reload=True)
