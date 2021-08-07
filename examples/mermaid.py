import dash
import dash_html_components as html
from dash_extensions import Mermaid
from dash.dependencies import Output, Input

chart = """
graph TD;
A-->B;
A-->C;
B-->D;
C-->D;
"""
app = dash.Dash()
app.layout = html.Div([Mermaid(id="mermaid"), html.Button("Click me", id="trigger")])


@app.callback(Output("mermaid", "chart"), Input("trigger", "n_clicks"), prevent_initial_call=True)
def set_chart(_):
    return chart


if __name__ == "__main__":
    app.run_server(port=9998)
