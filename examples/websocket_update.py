import json
import dash_html_components as html
import random
import dash_core_components as dcc
import plotly.graph_objects as go
from gevent import sleep
from dash import Dash
from dash.dependencies import Input, Output, State
from dash_extensions import WebSocket
from dash_extensions.websockets import SocketPool, run_server


# Generator to simulate continuous data feed.
def data_feed():
    while True:
        sleep(random.uniform(0, 2))  # delay between data events
        yield random.uniform(0, 1)  # the data value


# This block runs asynchronously.
def ws_handler(ws):
    for data in data_feed():
        ws.send(json.dumps(data))  # send data


# Create example app.
app = Dash(prevent_initial_callbacks=True)
socket_pool = SocketPool(app, handler=ws_handler)
app.layout = html.Div([dcc.Graph(id="graph", figure=go.Figure(go.Scatter(x=[], y=[]))), WebSocket(id="ws")])


@app.callback(Output("graph", "figure"), [Input("ws", "message")], [State("graph", "figure")])
def update_graph(msg, figure):
    x, y = figure['data'][0]['x'], figure['data'][0]['y']
    return go.Figure(data=go.Scatter(x=x + [len(x)], y=y + [float(msg['data'])]))


if __name__ == '__main__':
    run_server(app, port=5000)  # 5000 if the default port
