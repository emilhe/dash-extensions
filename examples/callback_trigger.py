import dash_html_components as html
from dash_extensions.enrich import Output, Dash, Trigger

app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    html.Button("Click me", id="btn"), html.Div(id="log")
])


@app.callback(Output("log", "children"), Trigger("btn", "n_clicks"))
def func():  # argument is omitted from the function
    return "You clicked the button"


if __name__ == '__main__':
    app.run_server()
