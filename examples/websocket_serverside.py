import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import Input, Output
from dash_extensions import WebSocket

# Create example app.
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    dcc.Input(id="input", autoComplete="off"), html.Div(id="message"),
    WebSocket(url="wss://echo.websocket.org", id="ws")
])


@app.callback(Output("ws", "send"), [Input("input", "value")])
def send(value):
    return value


@app.callback(Output("message", "children"), [Input("ws", "message")])
def message(e):
    return f"Response from websocket: {e['data']}"


if __name__ == '__main__':
    app.run_server()
