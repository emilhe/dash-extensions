import dash
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Output, Input, State

# Some dummy data.
from dash_extensions.callback import DashCallbackBlueprint

data_map = {"Nordics": ["Sweden", "Norway", "Denmark"], "Europe": ["Germany", "France", "Spain"]}
region_options = [{"value": item, "label": item} for item in list(data_map.keys())]
country_options = lambda x: [{"value": item, "label": item} for item in data_map[x]] if x is not None else []
# Drop down constructors.
region_dd = lambda i: dcc.Dropdown(placeholder="Select region", id="region{}".format(i), options=region_options)
country_dd = lambda i: dcc.Dropdown(placeholder="Select country", id="country{}".format(i), options=region_options)
# Create app.
css = ["https://maxcdn.bootstrapcdn.com/font-awesome/4.2.0/css/font-awesome.min.css"]
app = dash.Dash(__name__, external_stylesheets=css)
app.config['suppress_callback_exceptions'] = True
# Create layout.
app.layout = html.Div([
    region_dd(1), html.Button("Copy values", id="copy"), region_dd(2), country_dd(1), html.Div(), country_dd(2)
], style={"display": "grid", "grid-template-columns": "1fr 1fr 1fr", "width": "100%"})
# Callbacks for left controller.
app.callback(Output("country1", "options"), [Input("region1", "value")])(country_options)


def setup_callbacks_for_right_controller(app):
    app.callback(Output("country2", "options"), [Input("region2", "value")])(country_options)
    app.callback(Output("region2", "value"), [Input("copy", "n_clicks")], [State("region1", "value")])(lambda x, y: y)
    app.callback([Output("country2", "options"), Output("country2", "value")], [Input("copy", "n_clicks")],
                 [State("country1", "options"), State("country1", "value")])(lambda x, y, z: [y, z])


# setup_callbacks_for_right_controller(app)  # throws dash.exceptions.DuplicateCallbackOutput

# Proposed solution.
dcb = DashCallbackBlueprint()
setup_callbacks_for_right_controller(dcb)
dcb.register(app)

if __name__ == '__main__':
    app.run_server()
