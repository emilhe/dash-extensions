import dash
import dash_core_components as dcc
import dash_html_components as html

from dash_extensions.enrich import Dash, Output, Input, State
from dash_extensions.enrich_composed import ComposedComponentMixin, Alias


class EnhanceSlider(ComposedComponentMixin, html.Div):
    """Example component enhancing a standard slider with an input field, both being updatable and kept in sync.

    Inspired by https://community.plotly.com/t/problem-with-circular-callbacks-slider-changes-input-and-input-changes-slider/39685/2
    """

    # define the alias that will expose as the "value" property of the EnhanceSlider the value of the input
    _aliases = {"value": Alias("input", "value")}

    def layout(self, value):
        return html.Div(
            id="holder",
            children=[
                dcc.Slider(id="slider", min=0, max=100, value=0),
                dcc.Input(id="input", value=0),
            ],
        )

    @classmethod
    def declare_callbacks(cls):
        """Declare the callback that handles the sync of the two fields."""

        @cls.callback(
            Input("slider", "value"),
            Input("input", "value"),
            State("slider", "id"),
            State("input", "id"),
            Output("holder", "children"),
        )
        def sync_values(slider, input, slider_id, input_id):
            # get the dependency that has triggered the callback
            trigger_id = dash.callback_context.triggered[0]["prop_id"]

            try:
                # get the value of the triggered input
                value = int(dash.callback_context.inputs[trigger_id])
            except KeyError:
                # happens in case of trigger_id="." (initial trigger)
                return dash.no_update

            # overwrite the components with new components
            # reusing the ids of the initial components (as ids have been mangled)
            return [
                dcc.Slider(id=slider_id, min=0, max=100, value=value),
                dcc.Input(id=input_id, value=value),
            ]


app = Dash(
    __name__,
    title="Enhance slider demo",
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
)

app.layout = html.Div(
    [
        html.H1("Enhanced Slider demo"),
        html.P(
            "The EnhanceSlider component proposes both a slider "
            "and an input to define a value, with both fields synchronised."
        ),
        html.Div(id="inject"),
        EnhanceSlider(id="first"),
    ]
)


@app.callback(Input("first", "value"), Output("inject", "children"))
def refresh_label(value):
    return f"The value of the enhanced slider is {value}"


if __name__ == "__main__":
    app.run_server(debug=True, dev_tools_hot_reload=True, port=8055)
