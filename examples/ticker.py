import dash
import dash_html_components as html
from dash_extensions import Ticker

app = dash.Dash(__name__)
app.layout = html.Div(Ticker([html.Div("Some text")], direction="toRight"))

if __name__ == '__main__':
    app.run_server()