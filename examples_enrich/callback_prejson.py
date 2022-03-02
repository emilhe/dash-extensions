import itertools
import plotly.graph_objs as go
import pandas as pd
import numpy as np

from dash import html, dcc
from dash_extensions.enrich import Dash, Output, Trigger, plotly_jsonify


def make_figure():
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col]))
    return fig


def make_layout(tag):
    return [dcc.Graph(id=f"graph_{tag}"), html.Button(f"Update [{tag}]", id=f"btn_{tag}")]


tags = ["default", "memoize", "prejson"]
memoize = dict(default=None, memoize=True, prejson=plotly_jsonify)
# Create dummy data.
df = pd.DataFrame(index=pd.date_range("2020-01", "2021-01", freq="H"), columns=list("ABCDEFGHIJK"), data=pd.np.nan)
df[:] = np.random.random(df.values.shape)
# Create example app.
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div(list(itertools.chain.from_iterable([make_layout(tag) for tag in tags])))
# Attach callbacks.
for t in tags:
    app.callback(Output(f"graph_{t}", "figure"), Trigger(f"btn_{t}", "n_clicks"), memoize=memoize[t])(make_figure)

if __name__ == "__main__":
    app.run_server(port=8877, debug=True)
