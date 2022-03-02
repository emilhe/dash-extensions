import asyncio
import random
import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

app = Starlette(middleware=[Middleware(CORSMiddleware, allow_origins=["*"])])


async def numbers():
    while True:
        await asyncio.sleep(1)
        yield [random.randrange(200, 1000) for _ in range(10)]


@app.route("/")
async def sse(request):
    generator = numbers()
    return EventSourceResponse(generator)


if __name__ == "__main__":
    uvicorn.run(app, port=8000)
