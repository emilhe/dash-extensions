import dash
import dash_core_components as dcc
import dash_html_components as html
from examples import calculator_csf

from dash.dependencies import Output, Input
from dash_extensions.transpile import module_to_clientside_functions, inject_js

# Create example app.
app = dash.Dash()
app.layout = html.Div([
    dcc.Input(id="a", value=2, type="number"), html.Div("+"),
    dcc.Input(id="b", value=2, type="number"), html.Div("="), html.Div(id="c"),
])
# Create clientside callback.
inject_js(app, module_to_clientside_functions(calculator_csf))
app.clientside_callback(calculator_csf.add, Output("c", "children"), [Input("a", "value"), Input("b", "value")])

if __name__ == '__main__':
    app.run_server(port=7878)
