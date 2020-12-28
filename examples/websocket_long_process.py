import json
import dash_html_components as html
import dash_extensions as de

from gevent import sleep
from dash import Dash
from dash.dependencies import Input, Output
from dash_extensions.socket import SocketPool, run_server


def long_calculation(msg, ws):
    sleep(2)  # Delay message to simulate a long calculation
    ws.send(f"Calculation completed: {msg}")


# Create example app.
app = Dash(prevent_initial_callbacks=True)
socket_pool = SocketPool(app, message_handler=long_calculation)
# Create example app.
app.layout = html.Div([html.Button("Run", id="btn"), html.Div(id="msg"), de.DashWebSocket(id="ws")])


@app.callback(Output("ws", "send"), [Input("btn", "n_clicks")])
def start_calc(n_clicks):
    return n_clicks


@app.callback(Output("msg", "children"), [Input("ws", "message")])
def show_result(result):
    return json.dumps(result)


if __name__ == '__main__':
    run_server(app)
