from dash import Dash, html, Input, Output, dcc
from dash_extensions import WebSocket

# The url of server that emits the events.
sse_url = "http://127.0.0.1:8000"
# Create small example app.
app = Dash(__name__)
app.layout = html.Div([dcc.Graph(id="graph"), DashEventSource(id="sse", url=sse_url)])
# You could also use a normal callback, but client side callbacks yield better performance.
app.clientside_callback(
    """
    function(val) {
        values = val ? JSON.parse(val) : []
        return {data: [{y: values , type: "scatter"}]}
    }
    """,
    Output("graph", "figure"),
    Input("sse", "message"),
)

if __name__ == "__main__":
    app.run_server()
