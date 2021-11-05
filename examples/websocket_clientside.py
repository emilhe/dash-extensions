import dash_extensions as de
from dash import html, dcc, Dash, Input, Output

# Create example app.
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    dcc.Input(id="input", autoComplete="off"), html.Div(id="msg"),
    de.WebSocket(url="wss://echo.websocket.org", id="ws")
])
# Send input value using websocket.
send = "function(value){return value;}"
app.clientside_callback(send, Output("ws", "send"), [Input("input", "value")])
# Update div using websocket.
receive = "function(msg){return \"Response from websocket: \" + msg.data;}"
app.clientside_callback(receive, Output("msg", "children"), [Input("ws", "message")])

if __name__ == '__main__':
    app.run_server()
