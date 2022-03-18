import asyncio
import time

import pytest
import uvicorn

from multiprocessing import Process
from sse_starlette import EventSourceResponse
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from dash_extensions import EventSource
from dash import Dash, Input, Output, html, dcc

# region Server fixture

middleware = Middleware(CORSMiddleware, allow_origins=["*"], allow_headers=["*"])
starlette = Starlette(middleware=[middleware])
server_port = 5001
server_url = f"http://127.0.0.1:{server_port}"
sse_response = "Hello world!"


async def hello_world():
    while True:
        await asyncio.sleep(1)
        yield sse_response


@starlette.route("/")
async def sse(request):
    generator = hello_world()
    return EventSourceResponse(generator)


def run_server():
    uvicorn.run(starlette, port=server_port)


@pytest.fixture
def server():
    proc = Process(target=run_server, args=(), daemon=True)
    proc.start()
    yield
    proc.kill()  # Cleanup after test


# endregion

def test_server_sent_events(dash_duo, server):
    # Create small example app.
    app = Dash(__name__)
    app.layout = html.Div([html.Div(id="log"), EventSource(id="sse", url=server_url)])
    # You could also use a normal callback, but client side callbacks yield better performance.
    app.clientside_callback("function(x){return x;}", Output("log", "children"), Input("sse", "message"))

    dash_duo.start_server(app)
    time.sleep(0.01)
    assert dash_duo.find_element("#log").text == ""
    dash_duo.wait_for_text_to_equal("#log", sse_response, timeout=10)
