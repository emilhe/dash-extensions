from dash import Dash, Input, Output, dcc
import dash_html_components as html

app = Dash(__name__)
app.layout = html.Div([dcc.Input(id="input", value="my-value"), html.Div(id="output")])


@app.callback(Output("output", "children"), [Input("input", "value")])
def display_output(value):
    return f"You have entered {value}"


if __name__ == "__main__":
    app.run_server(debug=True)
