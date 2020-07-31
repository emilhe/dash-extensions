import dash_html_components as html
from dash_extensions.enrich import Output, Dash, Trigger

app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    html.Button("Left", id="left"), html.Button("Right", id="right"), html.Div(id="log"),
])


@app.callback(Output("log", "children"), Trigger("left", "n_clicks"), group="lr")  # targets same output as right
def left():
    return "left"


@app.callback(Output("log", "children"), Trigger("right", "n_clicks"), group="lr")  # targets same output as left
def right():
    return "right"


if __name__ == '__main__':
    app.run_server()

