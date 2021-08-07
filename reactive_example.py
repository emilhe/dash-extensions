import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash_extensions.enrich import Dash, Output, Input

app = Dash()
app.layout = html.Div([dcc.Input(value=1, id='x', type='number'),
                       dcc.Input(value=1, id='power', type='number'),
                       html.Div(id='result'), dcc.Graph(id='graph')])

@app.reactive(Input('x'), Input('power'))
def z(x, y):
    return x ** y if (x and y) else None

#app.clientside_reactive("z", "function(x,y){return x**y}", Input('x'), Input('power')) ??

@app.callback(Output('result'), Input('x'), Input('power'), Input('z'))
def display_result(x, y, z):
    return f"{x}^{y} is {z}"

@app.callback(Output('graph', 'figure'), Input('x'), Input('power'), Input('z'))
def plot_result(x, y, z):
    return go.Figure([go.Bar(x=['x', 'y', 'x**y'], y=[x, y, z])])

if __name__ == "__main__":
    app.run_server()