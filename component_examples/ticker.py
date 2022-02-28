from dash import Dash, html
from dash_extensions import Ticker

app = Dash(__name__)
app.layout = html.Div(Ticker([html.Div("Some text")], direction="toRight"))

if __name__ == "__main__":
    app.run_server()
