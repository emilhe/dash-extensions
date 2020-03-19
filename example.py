import dash
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
from extensions import DashCallbackBlueprint

# Some dummy data.
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
# Callbacks for left controller (populate country dd on region selection).
app.callback(Output("country1", "options"), [Input("region1", "value")])(country_options)

# region Callbacks for right controller

new_syntax = True


def current_syntax():
    def update(region, n_clicks, options, country):
        if region is None and n_clicks is None:
            raise PreventUpdate
        triggered_name = dash.callback_context.triggered[0]['prop_id']
        """
        Since this callback is a composition of two logic operations, the action is delegated based on the input trigger.
        """
        if triggered_name == "region2.value":
            return country_options(region), dash.no_update
        if triggered_name == "copy.n_clicks":
            return options, country
        raise PreventUpdate

    """ 
    Callback to copy region selection. Even though this operation is logically related to copying the country 
    selection, these operations cannot be merged into the same callback; would cause "same input/output" error. 
    """
    app.callback(Output("region2", "value"), [Input("copy", "n_clicks")], [State("region1", "value")])(lambda x, y: y)
    """ 
    Callback to (1) copy country selection (value, options) and (2) to update country dd on region selection. These two
    (logically separate) operations cannot be split in two callback; would cause "output assigned multiple times" error.
    """
    app.callback([Output("country2", "options"), Output("country2", "value")],
                 [Input("region2", "value"), Input("copy", "n_clicks")],
                 [State("country1", "options"), State("country1", "value")])(update)


def alternative_syntax():
    # Create a blue print for storing the callback operations.
    dcb = DashCallbackBlueprint()
    # Callback to populate country dd on region selection.
    dcb.callback(outputs=[("country2", "options")], inputs=[("region2", "value")], func=lambda x: country_options(x))
    # Callback to copy region selection.
    dcb.callback(outputs=[("region2", "value")], inputs=[("copy", "n_clicks")], states=[("region1", "value")],
                 func=lambda x, y: y)
    # Callback to copy country selection.
    dcb.callback(outputs=[("country2", "options"), ("country2", "value")], inputs=[("copy", "n_clicks")],
                 states=[("country1", "options"), ("country1", "value")], func=lambda x, y, z: [y, z])
    # Register the blue print on the application.
    dcb.register(app)


if new_syntax:
    alternative_syntax()
else:
    current_syntax()

# endregion

if __name__ == '__main__':
    app.run_server()
