import json
from dash_extensions.enrich import DashProxy, html, dcc, Output, Input, State, MultiplexerTransform, ContainerTransform, \
    ListOutput


class ListEmulator:
    def __init__(self):
        self.actions = []

    def append(self, item):
        self.actions.append(dict(action="append", item=item))

    def extend(self, iterable):
        self.actions.append(dict(action="extend", array=list(iterable)))

    def clear(self):
        self.actions.append(dict(action="clear"))

    def sort(self):
        self.actions.append(dict(action="sort"))

    def reverse(self):
        self.actions.append(dict(action="reverse"))


target_id = "store"
app = DashProxy(transforms=[MultiplexerTransform(), ContainerTransform()])
app.layout = html.Div([
    html.Button("Add", id="btn_append"),
    html.Button("Concat", id="btn_concat"),
    html.Button("Sort", id="btn_sort"),
    html.Button("Reverse", id="btn_reverse"),
    html.Button("Clear", id="btn_clear"),
    dcc.Store(id=target_id, data=[]),
    html.Div(id="log"),
])


@app.callback(ListOutput("store_relay", "data"), Input("btn_append", "n_clicks"))
def btn_append(n_clicks):
    le = ListEmulator()  # LIBRARY

    le.append(n_clicks)

    return le.actions  # LIBRARY


@app.callback(Output("store_relay", "data"), Input("btn_concat", "n_clicks"))
def btn_extend(n_clicks):
    le = ListEmulator()  # LIBRARY

    le.extend([n_clicks, n_clicks])

    return le.actions  # LIBRARY


@app.callback(Output("store_relay", "data"), Input("btn_sort", "n_clicks"))
def btn_sort(n_clicks):
    le = ListEmulator()  # LIBRARY

    le.sort()

    return le.actions  # LIBRARY


@app.callback(Output("store_relay", "data"), Input("btn_reverse", "n_clicks"))
def btn_reverse(n_clicks):
    le = ListEmulator()  # LIBRARY

    le.reverse()

    return le.actions  # LIBRARY


# region TODO: Move to library

app.layout.children += [dcc.Store(id="store_relay")]

# TODO: These are OUTPUT props
app.clientside_callback(f"""function(xs, current){{
    // Handle empty init call.
    if (typeof xs === 'undefined'){{
        return window.dash_clientside.no_update;
    }}
    // Handle non-list actions (most likely due to user error).
    if (!(Array.isArray(xs))){{
        console.log("Action input must be array for component {target_id}, but was not.");
        console.log(xs);
        console.log("Update will be skipped.");
        return window.dash_clientside.no_update;
    }}
    // Handle actions.
    for (const x of xs) {{
        switch(x.action) {{
          case "set":
            current = x;
            break;
          case "append":
            current.push(x.item)
            break;
          case "extend":
            current = current.concat(x.array);
            break;
          case "insert":
            current = current.splice(x.index, 0, x.value);
            break;
          case "remove":
            current = current.filter(function(ele){{
                return ele != x.value;
            }});
          case "pop":
            current.splice(x.index, 1);
          case "reverse":
            current.reverse();
          case "sort":
            // TODO: Make it possible to inject sorting function
            current.sort();
          case "clear":
            current = []             
          default:
            console.log("Received unknown action for component {target_id}.");
            console.log(x);
            console.log("Update will be skipped.");
        }}
    }}
    return current;
}}""", Output(target_id, "data"), Input("store_relay", "data"), State(target_id, "data"))


# TODO: These are INPUT props
# len, count, min, max

# endregion

@app.callback(Output("log", "children"), Input("store", "data"))
def update_log(data):
    return json.dumps(data)


if __name__ == '__main__':
    app.run_server()
