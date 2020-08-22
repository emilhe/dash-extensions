import dash
import dash_core_components as dcc
import dash_html_components as html
import logic

from dash.dependencies import Output, Input
from dash_extensions.transpile import to_clientside_functions, inject_js

# Create example app..
app = dash.Dash()
app.layout = html.Div([
    dcc.Input(id="a", value=2, type="number"), html.Div("+"),
    dcc.Input(id="b", value=2, type="number"), html.Div("="), html.Div(id="c"),
])
# Create clientside callback.
inject_js(app, to_clientside_functions(logic))
app.clientside_callback(logic.add, Output("c", "children"), [Input("a", "value"), Input("b", "value")])

if __name__ == '__main__':
    app.run_server(port=7878)
