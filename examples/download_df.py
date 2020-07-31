import dash
import pandas as pd
import dash_html_components as html

from dash.dependencies import Output, Input
from dash_extensions import Download
from dash_extensions.snippets import send_data_frame

# Example data.
df = pd.DataFrame({'a': [1, 2, 3, 4], 'b': [2, 1, 5, 6], 'c': ['x', 'x', 'y', 'y']})
# Create app.
app = dash.Dash(prevent_initial_callbacks=True)
app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])


@app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
def func(n_clicks):
    return send_data_frame(df.to_excel, "mydf.xls")


if __name__ == '__main__':
    app.run_server()
