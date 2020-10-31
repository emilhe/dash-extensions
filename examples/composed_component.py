import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import State, ALL
from dash.exceptions import PreventUpdate

from dash_extensions.enrich import Dash, Output, Input
from enrich_composed import ComposedComponentMixin


class EnhanceSlider(ComposedComponentMixin, html.Div):
    """Example component enhancing a standard Slider and that exposes two properties (hiding the others):
    - size: the max size of its internal slider
    - info: a string with the result of the slider
    """

    _properties = ["info"]
    _aliases = {"value": ("input_size", "value"),
                "size": ("slider", "max")}
    _composed_type = "enhance-slider"

    def layout(self, info, size, value):
        return [
            dcc.Slider(id="slider", min=0, max=size, value=value),
            html.Label("Enter size", id="label2"),
            dcc.Input(id="input_size", value=size),
        ]

    @classmethod
    def declare_callbacks(cls, app):
        """Declare the declare_callbacks that will handle the update of the size and info properties."""

        @app.callback(Input("slider", "max"), Output("slider", "marks"), Output("slider", "value"))
        def size_setter(size):
            if size:
                size = int(size)
                return {i: f"{i}" for i in range(0, size + 1)}, size / 2
            raise PreventUpdate()

        @app.callback(Input("input_size", "value"), Output("self", "size"))
        def size_getter(size, ):
            if size:
                return int(size)
            raise PreventUpdate()

        @app.callback(
            Input("slider", "value"),
            Input("self", "size"),
            Output("self", "info"),
        )
        def info_getter(value, total):
            return f"{value} / {total}"


app = Dash(
    __name__,
    title="Composed Component cc",
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
)

# cc.register_composed_component(EnhanceSlider(id="any"))
# cc.register_composed_component(EnhanceSlider(id={"index": "any"}))

app.layout = html.Div(
    [
        # EnhanceSlider(id="first", size=4),
        # EnhanceSlider(id="second", size=10),
        html.Button(id="btn", children="Click me"),
        html.Div(id="inject"),
        # EnhanceSlider(id={"index": "first"}, size=4),
        # EnhanceSlider(id={"index": "second"}, size=10),
        html.Label(id="out"),
    ]
)


@app.callback(Input("btn", "n_clicks"),
              State("inject", "children"),
              Output("inject", "children"))
def add_composed_components(n_clicks, children):
    if n_clicks:
        children = children or []
        return children + [EnhanceSlider(id={"index": i+len(children)}, size=5+len(children)) for i in range(2)]
    raise PreventUpdate


@app.callback(
    Input({"index": ALL}, "info"),
    State({"index": ALL}, "value"),
    Output("out", "children"),
)
def update_out(infos, value):
    return f"You have chosen '{infos}' (value of first = {value})"


#
# @cc.callback(Input({"index": "first"}, "info"), Output({"index": "second"}, "value"))
# def update_out(info2):
#     value_str = info2.split(" / ")[0]
#     try:
#         return int(value_str)
#     except ValueError:
#         raise PreventUpdate()


if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_hot_reload=True)
