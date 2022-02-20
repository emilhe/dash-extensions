import json
import dash_html_components as html

from gevent import sleep
from dash import Dash
from dash.dependencies import Input, Output
from dash_extensions import WebSocket
from dash_extensions.websockets import SocketPool, run_server


def ws_handler(ws):
    msg = ws.receive()  # receive input data
    sleep(2)  # add delay to simulate a long calculation
    ws.send(f"Calculation completed: {msg}")  # send output data


# Create example app.
app = Dash(prevent_initial_callbacks=True)
socket_pool = SocketPool(app, handler=ws_handler)
# Create example app.
app.layout = html.Div([html.Button("Run", id="btn"), html.Div(id="msg"), WebSocket(id="ws")])


@app.callback(Output("ws", "send"), [Input("btn", "n_clicks")])
def start_calc(n_clicks):
    return n_clicks  # by sending data (n_clicks) to the "send" prop of ws, the "ws_handler" is invoked


@app.callback(Output("msg", "children"), [Input("ws", "message")])
def show_result(result):
    return json.dumps(result)  # the "message" prop of ws triggers this callback when "ws_handler" invokes "send"


if __name__ == "__main__":
    run_server(app)
