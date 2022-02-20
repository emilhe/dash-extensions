import dash_html_components as html
from dash import Dash
from dash_extensions import BeforeAfter

app = Dash()
app.layout = html.Div([BeforeAfter(before="assets/lena_bw.png", after="assets/lena_color.png", width=512, height=512)])

if __name__ == "__main__":
    app.run_server()
