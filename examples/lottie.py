import dash
import dash_html_components as html
import dash_core_components as dcc

from dash_extensions import Lottie
from dash.dependencies import Input, Output

# Setup options.
url = "https://assets9.lottiefiles.com/packages/lf20_YXD37q.json"
options = dict(loop=True, autoplay=True, rendererSettings=dict(preserveAspectRatio='xMidYMid slice'))
# Create example app.
app = dash.Dash(__name__)
app.layout = html.Div([
    Lottie(options=options, width="25%", height="25%", url=url, id="lottie", speed=2),
    dcc.Slider(id="slider", value=20, min=0, max=100, step=1)
])


@app.callback(Output('lottie', 'speed'), [Input('slider', 'value')], prevent_initial_call=True)
def set_speed(value):
    if not value:
        return dash.no_update
    return value/10


if __name__ == '__main__':
    app.run_server(port=7879, debug=False)
