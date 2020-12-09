import dash_core_components as dcc
from dash import Dash
from dash.dependencies import Input, Output
from dash_extensions import Monitor

app = Dash()
app.layout = Monitor([
    dcc.Input(id="input", autoComplete="off", type="number", min=0, max=100, value=50),
    dcc.Slider(id="slider", min=0, max=100, value=50)],
    probes=dict(probe=[dict(id="input", prop="value"), dict(id="slider", prop="value")]), id="monitor")


@app.callback([Output("input", "value"), Output("slider", "value")], [Input("monitor", "data")])
def sync(data):
    probe = data["probe"]
    return probe["value"], probe["value"]


if __name__ == '__main__':
    app.run_server()
