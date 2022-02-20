import dash_html_components as html
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform

app = DashProxy(prevent_initial_callbacks=True, transforms=[MultiplexerTransform()])
app.layout = html.Div([html.Button("left", id="left"), html.Button("right", id="right"), html.Div(id="log")])


@app.callback(Output("log", "children"), Input("left", "n_clicks"))
def left(_):
    return "left"


@app.callback(Output("log", "children"), Input("right", "n_clicks"))
def right(_):
    return "right"


if __name__ == "__main__":
    app.run_server(debug=True, port=7777)
