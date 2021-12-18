import pandas as pd
import dash_bootstrap_components as dbc
import json

from dash import Dash, html, Input, Output, dash_table as dt
from dash.exceptions import PreventUpdate
from dash_extensions import EventListener

df = pd.read_csv("https://git.io/Juf1t")
df["id"] = df.index

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

table = dt.DataTable(
    id="tbl",
    data=df.to_dict("records"),
    columns=[{"name": i, "id": i} for i in df.columns],
)

listen_table = html.Div(
    [
        EventListener(
            id="el",
            events=[{"event": "click", "props": ["srcElement.className", "srcElement.innerText"]}],
            logging=True,
            children=table,
        )
    ]
)

app.layout = dbc.Container(
    [
        dbc.Label("Click a cell in the table:"),
        listen_table,
        dbc.Alert("Click the table", id="out"),
        html.Div(id="event"),
    ]
)


@app.callback(Output("event", "children"), Input("el", "event"), Input("el", "n_events"))
def click_event(event, n_events):
    # Check if the click is on the active cell.
    if not event or "cell--selected" not in event["srcElement.className"]:
        raise PreventUpdate
    # Return the content of the cell.
    return f"Cell content is {event['srcElement.innerText']}, number of clicks in {n_events}"


@app.callback(Output("out", "children"), Input("tbl", "active_cell"))
def update_graphs(active_cell):
    return json.dumps(active_cell)


if __name__ == "__main__":
    app.run_server(debug=True, port=7676)