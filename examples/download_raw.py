import dash
import dash_html_components as html

from dash.dependencies import Output, Input
from dash_extensions import Download

app = dash.Dash(prevent_initial_callbacks=True)
app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])


@app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
def func(n_clicks):
    return dict(content="Hello world!", filename="hello.txt")


if __name__ == '__main__':
    app.run_server()
