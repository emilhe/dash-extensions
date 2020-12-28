import dash_html_components as html
import dash_extensions as de

from dash import Dash
from dash.dependencies import Input, Output
from dash_extensions.socket import SocketPool, run_server

# Create example app.
app = Dash(prevent_initial_callbacks=True)
socket_pool = SocketPool(app)
# Create example app.
app.layout = html.Div([html.Div(id="msg"), de.DashWebSocket(id="ws")])
# Update div using websocket.
app.clientside_callback("function(msg){return \"Response from websocket: \" + msg.data;}",
                        Output("msg", "children"), [Input("ws", "message")])


# End point to push messages.
@app.server.route("/send/<message>")
def send_message(message):
    socket_pool.send_all(message)
    return f"Message [{message}] sent."


if __name__ == '__main__':
    run_server(app)
