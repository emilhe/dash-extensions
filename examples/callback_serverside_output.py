import time
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
from dash_extensions.enrich import Dash, Output, Input, ServersideOutput

app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    html.Button("Query data", id="btn"), dcc.Dropdown(id="dd"), dcc.Graph(id="graph"),
    dcc.Loading(dcc.Store(id='store'), fullscreen=True, type="dot")
])


@app.callback(ServersideOutput("store", "data"), Input("btn", "n_clicks"))
def query_data(n_clicks):
    time.sleep(1)
    return px.data.gapminder()  # no JSON serialization here


@app.callback(Input("store", "data"), Output("dd", "options"))
def update_dd(df):
    return [{"label": column, "value": column} for column in df["year"]]  # no JSON de-serialization here


@app.callback(Output("graph", "figure"), [Input("store", "data"), Input("dd", "value")])
def update_graph(df, value):
    df = df.query("year == {}".format(value))  # no JSON de-serialization here
    return px.sunburst(df, path=['continent', 'country'], values='pop', color='lifeExp', hover_data=['iso_alpha'])


if __name__ == '__main__':
    app.run_server()
