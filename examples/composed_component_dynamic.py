"""Test for adding new ComposedComponentMixin through a callback.

It shows the use of the 'wrap' functionality to mangle the names
 of the components inside a ComposedComponentMixin."""
import logging
import sys

import dash_core_components as dcc
import dash_html_components as html
from dash import no_update
from dash.dependencies import State, ALL

from dash_extensions.enrich import Dash, Output, Input
from dash_extensions.enrich_composed import ComposedComponentMixin, logger, wrap


class ButtonToggle(ComposedComponentMixin, html.Button):
    """Button that changes state when clicked."""

    _properties = ["state"]

    def layout(self, **kwargs):
        return html.Div(id="label", children=["Click me to toggle"])

    @classmethod
    def declare_callbacks(cls):
        """Declare the declare_callbacks that will handle the update of the size and info properties."""

        @cls.callback(Input("self", "n_clicks"), State("self", "state"), Output("self", "state"))
        def flip_button_state(n_clicks, state):
            if n_clicks:
                return not bool(state)
            return no_update

        @cls.callback(Input("self", "state"), State("self", "id"), Output("label", "children"))
        def set_label(state, btn_id):
            return [f"I'm {state} {btn_id}"]


class Flagger(ComposedComponentMixin, html.Div):
    _properties = ["flags"]

    def layout(self, flags):
        if flags is None:
            flags = []
        flags = [ButtonToggle(id={"type": "flag", "id": f}) for f in flags] + [
            html.Label(id={"label-id": "init"}, children=[f"This is label for init"])
        ]

        return [dcc.Input(id="new-flag", debounce=True), html.Div(id="flag-div", children=flags)]

    @classmethod
    def declare_callbacks(cls):
        @cls.callback(
            Input("new-flag", "value"),
            State("self", "id"),
            State("flag-div", "children"),
            Output("flag-div", "children"),
        )
        def add_flag(flag_name, self_id, flags):
            if flag_name:
                new_button = wrap(self_id, ButtonToggle(id={"type": "flag", "id": flag_name}))
                new_label = wrap(
                    self_id,
                    html.Label(
                        id={"label-id": flag_name},
                        children=[f"This is label for {flag_name}"],
                    ),
                )
                return flags + [new_button, new_label]
            return no_update

        @cls.callback(
            Input({"type": "flag", "id": ALL}, "state"),
            State({"label-id": ALL}, "children"),
            # State("self", "children"),
            Output("self", "flags"),
        )
        def update_flags(flags, labels):
            return flags + labels


app = Dash(
    __name__,
    title="Composed Component cc",
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
)

app.layout = html.Div([Flagger(id="flagger", flags=["mine"]), html.Label(id="flagger-out")])


@app.callback(Input("flagger", "flags"), Output("flagger-out", "children"))
def update_out(flags):
    return f"You have chosen '{flags}'"


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # app._setup_server()
    app.run_server(debug=True, dev_tools_hot_reload=True)
