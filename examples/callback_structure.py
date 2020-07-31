import dash_html_components as html
from dash_extensions.enrich import Output, Dash, Input

app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    html.Button("Click me", id="btn"), html.Div(id="log")
])


@app.callback(Input("btn", "n_clicks"), Output("log", "children"))  # inverted order of Output/Input is OK
def func(n_clicks):
    return f"Click count = {n_clicks}"


if __name__ == '__main__':
    app.run_server()
