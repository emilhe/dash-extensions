import time

from dash_extensions.enrich import DashProxy, dcc, html, Output, Input, BlockingCallbackTransform


app = DashProxy(transforms=[BlockingCallbackTransform()])
app.layout = html.Div([
    html.Div(id="output"),
    dcc.Interval(id="trigger")
])


@app.callback(Output("output", "children"), Input("trigger", "n_intervals"), blocking=True)
def update(n_intervals):
    print("INVOKING CALLBACK")
    time.sleep(5)
    return f"Hello! (n_intervals is {n_intervals})"


if __name__ == '__main__':
    app.run_server(debug=False)
