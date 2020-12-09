from enrich import Input, Output

import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc


def layout(*args, **kwargs):
    return dbc.Container([
        dbc.Row(html.Br()),
        dbc.Row(dcc.Input(id="input"), justify="around"),
        dbc.Row(html.Div(id="output"), justify="around"),
    ], fluid=True)


def callbacks(app):
    @app.callback(Output("output", "children"), [Input("input", "value")])
    def hello(value):
        return f"PAGE says: Hello {value}!"
