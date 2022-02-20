import json
import dash_leaflet as dl

from dash import html, Dash
from examples import geojson_csf
from dash_extensions.transpile import inject_js, module_to_props

# Create geojson.
with open("assets/us-states.json", "r") as f:
    data = json.load(f)
js = module_to_props(geojson_csf)  # do transcrypt to enable passing python functions as props
geojson = dl.GeoJSON(data=data, id="geojson", options=dict(style=geojson_csf.style), hoverStyle=geojson_csf.hover_style)
# Create app.
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div(
    [dl.Map(children=[dl.TileLayer(), geojson], center=[39, -98], zoom=4, id="map")],
    style={"width": "100%", "height": "50vh", "margin": "auto", "display": "block"},
)
# Inject transcrypted javascript.
inject_js(app, js)

if __name__ == "__main__":
    app.run_server(port=7777, debug=True)
