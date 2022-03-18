import asyncio
import logging

import uvicorn
from sse_starlette import EventSourceResponse
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

middleware = Middleware(CORSMiddleware, allow_origins=["*"], allow_headers=["*"])
async_server = Starlette(middleware=[middleware])
sse_response = "Hello world!"


def ws_response(msg):
    return f"Hello {msg}!"


async def hello_world():
    while True:
        await asyncio.sleep(1)
        yield sse_response


@async_server.route("/")
async def sse(request):
    generator = hello_world()
    return EventSourceResponse(generator)


@async_server.websocket_route("/ws")
async def websocket_endpoint(websocket):
    await websocket.accept()
    while True:
        msg = await websocket.receive_text()
        await websocket.send_text(ws_response(msg))


if __name__ == "__main__":
    logging.basicConfig(format='{levelname:7} {message}', style='{', level=logging.INFO)
    uvicorn.run(async_server, port=5002, log_config=None)