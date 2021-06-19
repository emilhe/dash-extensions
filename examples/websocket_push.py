import dash_html_components as html

from dash import Dash
from dash.dependencies import Input, Output
from dash_extensions.websockets import SocketPool, run_server
from dash_extensions import WebSocket

# Create example app.
app = Dash(prevent_initial_callbacks=True)
socket_pool = SocketPool(app)
app.layout = html.Div([html.Div(id="msg"), WebSocket(id="ws")])
# Update div using websocket.
app.clientside_callback("function(msg){return \"Response from websocket: \" + msg.data;}",
                        Output("msg", "children"), [Input("ws", "message")])


# End point to send message to current session.
@app.server.route("/send/<message>")
def send_message(message):
    socket_pool.send(message)
    return f"Message [{message}] sent."


# End point to broadcast message to ALL sessions.
@app.server.route("/broadcast/<message>")
def broadcast_message(message):
    socket_pool.broadcast(message)
    return f"Message [{message}] broadcast."


if __name__ == '__main__':
    run_server(app)
