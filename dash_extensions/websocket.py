import uuid
import json
import secrets
from flask_sockets import Sockets
from flask import session
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler


def ensure_session_id():
    if "socket_id" not in session:
        session["socket_id"] = uuid.uuid4()


def add_ws_endpoint(sockets, pool, handler, endpoint):
    @sockets.route(endpoint)
    def open_socket(ws):
        pool[session["socket_id"]] = ws
        while not ws.closed:
            handler(ws)


class SocketPool:

    def __init__(self, app, handler=lambda ws: ws.receive(), endpoint="/ws"):
        # Set session secret.
        if not app.server.secret_key:
            app.server.secret_key = secrets.token_urlsafe(16)
        app.server.before_request(ensure_session_id)
        # Create sockets.
        self.sockets = Sockets(app.server)
        self.pool = {}
        # Add endpoint.
        add_ws_endpoint(self.sockets, self.pool, handler, endpoint)

    def send(self, message):
        self._try_send(message, session["socket_id"])

    def broadcast(self, message):
        for client_id in list(self.pool.keys()):
            self._try_send(message, client_id)

    def _try_send(self, message, client_id):
        ws = self.pool[client_id]
        if ws.closed:
            return self.pool.pop(client_id)
        ws.send(json.dumps(message))


def run_server(app, port=5000):
    server = pywsgi.WSGIServer(('', port), app.server, handler_class=WebSocketHandler)
    server.serve_forever()
