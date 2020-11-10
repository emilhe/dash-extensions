import dash
import dash_core_components as dcc
import dash_html_components as html

from dash_extensions import Linker

app = dash.Dash()
app.layout = Linker(children=[html.Div("Min"), html.Div("Max"), html.Div(), html.Div("Value"),
                              dcc.Input(id="min", value=0, type='number'),
                              dcc.Input(id="max", value=100, type='number'),
                              dcc.Slider(id="slider", min=0, max=100, value=50),
                              dcc.Input(id="val", value=50, type='number', min=0, max=100)],
                    links=[
                        [dict(id="val", prop="value"), dict(id="slider", prop="value")],
                        [dict(id="min", prop="value"), dict(id="slider", prop="min")],
                        [dict(id="max", prop="value"), dict(id="slider", prop="max")],
                        # [dict(id="val", prop="min"), dict(id="min", prop="value")],
                        # [dict(id="val", prop="max"), dict(id="max", prop="value")]
                    ],
                    style={"display": "grid", "grid-template-columns": "1fr 1fr 5fr 1fr"})

if __name__ == '__main__':
    app.run_server(debug=True)
