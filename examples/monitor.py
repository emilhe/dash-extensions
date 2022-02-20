from dash import Dash, no_update, dcc, html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from dash_extensions import Monitor

# Example app.
app = Dash()
app.layout = html.Div(
    Monitor(
        [
            dcc.Input(id="deg-fahrenheit", autoComplete="off", type="number"),
            dcc.Input(id="deg-celsius", autoComplete="off", type="number"),
        ],
        probes=dict(deg=[dict(id="deg-fahrenheit", prop="value"), dict(id="deg-celsius", prop="value")]),
        id="monitor",
    )
)


@app.callback([Output("deg-fahrenheit", "value"), Output("deg-celsius", "value")], [Input("monitor", "data")])
def sync_inputs(data):
    # Get value and trigger id from monitor.
    try:
        probe = data["deg"]
        trigger_id, value = probe["trigger"]["id"], float(probe["value"])
    except (TypeError, KeyError):
        raise PreventUpdate
    # Do the appropriate update.
    if trigger_id == "deg-fahrenheit":
        return no_update, (value - 32) * 5 / 9
    elif trigger_id == "deg-celsius":
        return value * 9 / 5 + 32, no_update


if __name__ == "__main__":
    app.run_server(debug=False)
