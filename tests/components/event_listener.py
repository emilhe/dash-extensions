import pandas as pd
from dash import Dash, Input, Output
from dash import dash_table as dt
from dash import html
from dash.exceptions import PreventUpdate

from dash_extensions import EventListener

# Create a small data table.
df = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/solar.csv")
table = dt.DataTable(
    df.to_dict("records"), [{"name": i, "id": i} for i in df.columns], id="tbl"
)
# The event(s) to listen to (i.e. click) and the prop(s) to record, i.e. the column name.
row_index = "srcElement.attributes.data-dash-row.value"
events = [{"event": "click", "props": [row_index]}]
# Create small example app.
app = Dash()
app.layout = html.Div(
    [
        EventListener(id="el", events=events, children=table, logging=True),
        html.Div(id="event"),
    ]
)


@app.callback(
    Output("event", "children"), Input("el", "event"), Input("el", "n_events")
)
def click_event(event, n_events):
    if not event:
        raise PreventUpdate
    return f"Row index is {event[row_index]}, number of clicks in {n_events}"


if __name__ == "__main__":
    app.run_server()
