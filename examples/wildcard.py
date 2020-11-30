from dash_extensions.enrich import Dash
from flask import Flask
import dash_html_components as html

from dash.dependencies import ALL, MATCH
from dash_extensions.enrich import Trigger, Input, Output

fapp = Flask(__name__)
app = Dash(__name__, server=fapp)
app.suppress_callback_exceptions = True


@app.callback(
    Output("out", "children"), Input(dict(type="delete", id=ALL), "n_clicks"), group="group"
)
def do(d):
    print("Triggered")
    return d


app.layout = html.Div([
    html.Button("B1", id=dict(type="delete", id="1")),
    html.Button("B2", id=dict(type="delete", id="2")),
    html.Div(id="out")
])

app.run_server(debug=False)
