import dash_html_components as html
from dash.dependencies import ClientsideFunction
from dash_extensions.enrich import Dash, Input

app = Dash(__name__, prevent_initial_callbacks=True)
app.layout = html.Div([
    html.Button("Click me", id="btn")
])


@app.callback(Input("btn", "n_clicks"))  # no Output is OK
def func(n_clicks):
    print(f"Click count = {n_clicks}")


# Clientside callback with literal JS code.
f = "function(n_clicks){console.log('Hello world! Click count = ' + n_clicks);}"
app.clientside_callback(f, Input("btn", "n_clicks"))  # no Output is OK

# Clientside callback reference to JS asset function.
app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="hello"),
    Input("btn", "n_clicks"),  # no Output is OK
)

if __name__ == '__main__':
    app.run_server(port=7777)
