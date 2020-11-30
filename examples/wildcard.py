from dash_extensions.enrich import Dash
from flask import Flask
import dash_html_components as html

from dash.dependencies import ALL, MATCH
from dash_extensions.enrich import Input, Output

fapp = Flask(__name__)
app = Dash(__name__, server=fapp)
app.suppress_callback_exceptions = True


@app.callback(Output("all", "children"),
              Input(dict(type="btn", id=ALL), "n_clicks"), group="A")
def all(args):
    print("ALL")
    return args


@app.callback(Output(dict(type="MATCH", id=MATCH), "children"),
              Input(dict(type="btn", id=MATCH), "n_clicks"), group="C")
def match(args):
    print("MATCH")
    return args


ids = [1, 2, 3]
app.layout = html.Div(
    [html.Button(f"Button{id}", id=dict(type="btn", id=id)) for id in ids] +
    [html.Div(children="ALL"), html.Div(id="all", children="all")] +
    [html.Div(children="MATCH")] +
    [html.Div(id=dict(type="MATCH", id=id)) for id in ids]
)

app.run_server()
