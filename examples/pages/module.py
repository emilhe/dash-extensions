import dash_bootstrap_components as dbc

from dash_extensions.enrich import Input, Output
from dash import html, dcc


def layout(*args, **kwargs):
    return dbc.Container(
        [
            dbc.Row(html.Br()),
            dbc.Row(dcc.Input(id="input"), justify="around"),
            dbc.Row(html.Div(id="output"), justify="around"),
        ],
        fluid=True,
    )


def callbacks(app):
    @app.callback(Output("output", "children"), [Input("input", "value")])
    def hello(value):
        return f"MODULE says: Hello {value}!"
