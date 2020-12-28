import uuid
import json
from flask_sockets import Sockets


def add_ws_endpoint(sockets, pool, message_handler):
    @sockets.route('/ws')
    def open_socket(ws):
        pool[uuid.uuid4().__str__()] = ws
        while not ws.closed:
            msg = ws.receive()  # needed to keep the connection open
            if message_handler:
                message_handler(msg, ws)


class SocketPool:

    def __init__(self, app, message_handler=None, endpoint="/ws"):
        self.sockets = Sockets(app.server)
        self.pool = {}
        self.message_handler = message_handler
        add_ws_endpoint(self.sockets, self.pool, self.message_handler)

    def send(self, client_id, message):
        if client_id not in self.pool:
            return
        self._try_send(message, client_id)

    def send_all(self, message):
        for client_id in list(self.pool.keys()):
            self._try_send(message, client_id)

    def _try_send(self, message, client_id):
        ws = self.pool[client_id]
        if ws.closed:
            return self.pool.pop(client_id)
        ws.send(json.dumps(message))


def run_server(app):
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 5000), app.server, handler_class=WebSocketHandler)
    server.serve_forever()
