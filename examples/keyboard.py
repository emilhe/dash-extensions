import dash
import dash_html_components as html
import json

from dash.dependencies import Output, Input
from dash_extensions import Keyboard

app = dash.Dash()
app.layout = html.Div([Keyboard(id="keyboard"), html.Div(id="output")])


@app.callback(Output("output", "children"), [Input("keyboard", "keydown")])
def keydown(event):
    return json.dumps(event)


if __name__ == '__main__':
    app.run_server()