import time
import dash_html_components as html
import dash_core_components as dcc
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform

# Small example app.
proxy_container = dcc.Loading()
app = DashProxy(transforms=[MultiplexerTransform(proxy_location=proxy_container)])
app.layout = html.Div([html.Button("left", id="left", n_clicks=0),
                       html.Button("right", id="right", n_clicks=0),
                       html.Div("Initial value", id="log"), proxy_container])
# Client side function.
f = "function(n_clicks){return 'left (' + n_clicks + ')';}"
app.clientside_callback(f, Output("log", "children"), Input("left", "n_clicks"), prevent_initial_call=True)


@app.callback(Output("log", "children"), Input("right", "n_clicks"), prevent_initial_call=True)
def right(n_clicks):
    time.sleep(2)
    return f"right ({n_clicks})"


if __name__ == '__main__':
    app.run_server(port=7777, debug=True)
