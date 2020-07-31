import dash_html_components as html
from dash_extensions.enrich import Output, Dash, Input

app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    html.Button("Click me", id="btn")
])


@app.callback(Input("btn", "n_clicks"))  # not Output is OK
def func(n_clicks):
    print(f"Click count = {n_clicks}")


if __name__ == '__main__':
    app.run_server()
