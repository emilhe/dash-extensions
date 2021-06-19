import time
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px

from dash_extensions.enrich import Output, Input, State, ServersideOutput, DashProxy, ServersideOutputTransform, \
    RedisStore

app = DashProxy(prevent_initial_callbacks=True, transforms=[
    ServersideOutputTransform(backend=RedisStore())
])
app.layout = html.Div([
    html.Button("Query data", id="btn"), dcc.Dropdown(id="dd"), dcc.Graph(id="graph"),
    dcc.Loading(dcc.Store(id='store'), fullscreen=True, type="dot")
])


@app.callback(ServersideOutput("store", "data"), Input("btn", "n_clicks"))
def query_data(n_clicks):
    print("QUERY DATA")
    time.sleep(1)
    return px.data.gapminder()  # no JSON serialization here


@app.callback(Input("store", "data"), Output("dd", "options"))
def update_dd(df):
    return [{"label": column, "value": column} for column in df["year"]]  # no JSON de-serialization here


@app.callback(Output("graph", "figure"), [Input("dd", "value"), State("store", "data")])
def update_graph(value, df):
    df = df.query("year == {}".format(value))  # no JSON de-serialization here
    return px.sunburst(df, path=['continent', 'country'], values='pop', color='lifeExp', hover_data=['iso_alpha'])


if __name__ == '__main__':
    app.run_server(port=9999)
