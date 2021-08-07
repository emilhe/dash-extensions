import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import dash_table
from dash_extensions.enrich import DashProxy, Output, Input, ServersideOutputTransform

# Read the full, complex dataset here (for the sake of simplicify, a small px dataset is used). ??
df_all = px.data.gapminder()
# Example app demonstrating how to share state between callbacks via a reactive variable.
app = DashProxy(transforms=[ServersideOutputTransform()])
app.layout = html.Div([
    dcc.Dropdown(options=[dict(value=x, label=x) for x in df_all.country.unique()], id="country", value="Denmark"),
    dcc.Graph(id='graph'),
    dash_table.DataTable(id='table', columns=[{"name": i, "id": i} for i in df_all.columns])
])

@app.reactive(Input('country'))  # default prop for input/state is "value"
def df_filtered(country):  # reactive variable name = function name
    return df_all[df_all.country == country]  # defaults to serverside output, i.e. json serialization is not needed

@app.callback(Output('table', 'data'), Input('df_filtered'))  # access reactive variable via it's ID
def update_table(df):
    return df.to_dict('records')  # the reactive variable was stored serverside, i.e. deserialize is not needed

@app.callback(Output('graph', 'figure'), Input('df_filtered'))
def update_graph(df):
    return px.bar(df, x='year', y='pop', color='gdpPercap')

if __name__ == "__main__":
    app.run_server()