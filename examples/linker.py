import dash
import dash_core_components as dcc

from dash_extensions import Linker

app = dash.Dash()
app.layout = Linker(children=[dcc.Input(id="input", value=50), dcc.Slider(id="slider", min=0, max=100, value=50)],
                    links=[[dict(id="input", prop="value"), dict(id="slider", prop="value")]])

if __name__ == '__main__':
    app.run_server()
