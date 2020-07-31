import dash
import dash_html_components as html

from dash.dependencies import Output, Input
from dash_extensions import Download
from dash_extensions.snippets import send_file


app = dash.Dash(prevent_initial_callbacks=True)
app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])


@app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
def func(n_clicks):
    return send_file("/home/emher/Documents/Untitled.png")


if __name__ == '__main__':
    app.run_server()
