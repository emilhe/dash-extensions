import time
import pytest
import uvicorn

from multiprocessing import Process
from dash_extensions import EventSource, WebSocket
from dash import Dash, Input, Output, html, dcc
from tests.mock_async import sse_response, async_server, ws_response

# region Async mock server fixture

server_port = 5001
sse_server_url = f"http://127.0.0.1:{server_port}"
ws_server_url = f"ws://127.0.0.1:{server_port}/ws"


def run_server():
    uvicorn.run(async_server, port=server_port)


@pytest.fixture(scope="module")
def server():
    proc = Process(target=run_server, args=(), daemon=True)
    proc.start()
    yield
    proc.kill()  # Cleanup after test


# endregion

def test_server_sent_events(dash_duo, server):
    # Create small example app.
    app = Dash(__name__)
    app.layout = html.Div([html.Div(id="log"), EventSource(id="sse", url=sse_server_url)])
    # You could also use a normal callback, but client side callbacks yield better performance.
    app.clientside_callback("function(x){return x;}", Output("log", "children"), Input("sse", "message"))
    # Run the test.
    dash_duo.start_server(app)
    time.sleep(0.01)
    assert dash_duo.find_element("#log").text == ""
    dash_duo.wait_for_text_to_equal("#log", sse_response, timeout=5)


def test_websocket(dash_duo, server):
    # Create small example app.
    app = Dash(prevent_initial_callbacks=True)
    app.layout = html.Div(
        [
            dcc.Input(id="input", autoComplete="off"),
            html.Div(id="msg"),
            WebSocket(url=ws_server_url, id="ws"),
        ]
    )
    # Send input value using websocket.
    send = "function(value){return value;}"
    app.clientside_callback(send, Output("ws", "send"), [Input("input", "value")])
    # Update div using websocket.
    receive = 'function(msg){return msg.data;}'
    app.clientside_callback(receive, Output("msg", "children"), [Input("ws", "message")])
    # Run the test.
    dash_duo.start_server(app)
    time.sleep(0.01)
    assert dash_duo.find_element("#msg").text == ""
    name = "x"
    dash_duo.find_element("#input").send_keys(name)
    dash_duo.wait_for_text_to_equal("#msg", ws_response(name), timeout=2)
