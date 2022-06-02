import json
from dash_extensions.enrich import DashProxy, html, dcc, Output, Input, State, MultiplexerTransform, ContainerTransform, \
    ListOutput


class ListAction:
    @staticmethod
    def append(item):
        return dict(action="append", item=item)

    @staticmethod
    def extend(iterable):
        return dict(action="extend", array=list(iterable))

    @staticmethod
    def clear():
        return dict(action="clear")

    @staticmethod
    def sort():
        return dict(action="sort")

    @staticmethod
    def reverse():
        return dict(action="reverse")


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


gui_actions = dict(
    append=lambda x: ListAction.append(x),
    extend=lambda x: ListAction.extend([x, x]),
    sort=lambda x: ListAction.sort(),
    reverse=lambda x: ListAction.reverse(),
    clear=lambda x: ListAction.clear(),
)

app = DashProxy(transforms=[MultiplexerTransform(), ContainerTransform()])
app.layout = html.Div([html.Button(k, id=f"btn_{k}") for k in gui_actions] + [
    dcc.Store(id="store", data=[]),
    html.Div(id="log"),
])

for k in gui_actions:
    app.callback(ListOutput("store", "data"), Input(f"btn_{k}", "n_clicks"))(gui_actions[k])


@app.callback(Output("log", "children"), Input("store", "data"))
def update_log(data):
    return json.dumps(data)


if __name__ == '__main__':
    app.run_server()
