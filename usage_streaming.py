from flask_cors import CORS

from dash_extensions import StreamingBuffer
from dash_extensions.enrich import DashProxy, Input, Output, html

# Client-side function (for performance) that updates the graph.
update_graph = """function(msg) {
    if (msg === undefined) return "No data yet.";
    return msg.toString();
}
"""
# Create small example app.
app = DashProxy(__name__)
CORS(app.server)
app.layout = html.Div(
    [
        StreamingBuffer(id="sse", url="http://127.0.0.1:8000/stream"),
        html.Div(id="sse-container"),
        html.Br(),
        html.Div("----------"),
        html.Br(),
        html.Div(id="sse-status"),
    ]
)
app.clientside_callback(
    update_graph, Output("sse-container", "children"), Input("sse", "value")
)
app.clientside_callback(
    update_graph, Output("sse-status", "children"), Input("sse", "done")
)

if __name__ == "__main__":
    app.run_server()
