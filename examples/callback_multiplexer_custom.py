import time

from dash import html, dcc
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform


def make_callback(out_id, in_id):
    @app.callback(Output(out_id, "children"), Input(in_id, "n_clicks"), prevent_initial_call=True)
    def func(n_clicks):
        time.sleep(1)
        return f"{in_id} ({n_clicks})"


def make_block(i):
    layout = [html.Button(f"left{i}", id=f"left{i}", n_clicks=0),
              html.Button(f"right{i}", id=f"right{i}", n_clicks=0),
              html.Div("Initial value", id=f"log{i}")]
    make_callback(f"log{i}", f"left{i}")
    make_callback(f"log{i}", f"right{i}")
    return layout


# Setup custom proxy wrappers to achieve different loading screens.
proxy_wrapper_map = {
    Output("log0", "children"): lambda proxy: dcc.Loading(proxy, type="dot", fullscreen=True),
    Output("log1", "children"): lambda proxy: dcc.Loading(proxy, type="graph", fullscreen=True),
    Output("log2", "children"): lambda proxy: dcc.Loading(proxy, type="cube", fullscreen=True)
}
# Create example app.
app = DashProxy(transforms=[MultiplexerTransform(proxy_wrapper_map=proxy_wrapper_map)])
app.layout = html.Div(make_block(0) + make_block(1) + make_block(2))

if __name__ == '__main__':
    app.run_server(port=7778, debug=True)
