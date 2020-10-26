import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import State
from dash.exceptions import PreventUpdate

from dash_extensions.enrich import Dash, Output, Input, ComposedComponentMixin


class EnhanceSlider(ComposedComponentMixin, html.Div):
    """Example component enhancing a standard Slider and that exposes two properties (hiding the others):
    - size: the max size of its internal slider
    - info: a string with the result of the slider
    """

    _properties = ["info", "size"]
    _aliases = {"proxy-value": ("slider", "value")}
    _composed_type = "enhance-slider"

    def layout(self, info, size):
        return [
            dcc.Slider(id="slider", min=0, max=size, value=0),
            html.Label("Enter size", id="label2"),
            dcc.Input(id="input_size", value=size),
        ]

    @classmethod
    def declare_callbacks(cls, app):
        """Declare the callbacks that will handle the update of the size and info properties."""

        @app.callback(Input("self", "size"), Output("slider", "max"), Output("slider", "marks"))
        def size_setter(size):
            if size:
                size = int(size)
                return size, {i: f"{i}" for i in range(0, size + 1)}
            raise PreventUpdate()

        @app.callback(Input("input_size", "value"), Output("self", "size"))
        def size_getter(size):
            return size

        @app.callback(
            # Input("slider", "value"),
            Input("self", "proxy-value"),
            Input("input_size", "value"), Output("self", "info")
        )
        def info_getter(value, total):
            return f"{value} / {total}"


app = Dash(
    __name__,
    title="Composed Component app",
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
)

app.layout = html.Div(
    [EnhanceSlider(id="first", size=4), EnhanceSlider(id="second", size=10), html.Label(id="out")]
)


@app.callback(Input("first", "info"), Input("second", "info"), State("first", "proxy-value"), Output("out", "children"))
def update_out(info1, info2, value):
    return f"You have chosen '{info1}' and '{info2}' (proxy-value={value})"


@app.callback(Input("second", "info"), Output("first", "proxy-value"))
def update_out(info2):
    return int(info2.split(" / ")[0])


# @app.callback(Input("first", "info"), Input("second", "info"), Output("out", "children"))
# def update_out(info1, info2):
#     return f"You have chosen '{info1}' and '{info2}'"


if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_hot_reload=True)
