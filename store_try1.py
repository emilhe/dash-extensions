import json
from dash_extensions.enrich import DashProxy, html, dcc, Output, Input, MultiplexerTransform, OperatorTransform, OperatorOutput, Operator


gui_actions = dict(
    append=lambda x: Operator().list.append(x), #.apply(),
    extend=lambda x: Operator().list.extend([x, x]).apply(),
    sort=lambda x: Operator().list.sort().apply(),
    reverse=lambda x: Operator().list.reverse().apply(),
    clear=lambda x: Operator().list.clear().apply(),
)

app = DashProxy(transforms=[MultiplexerTransform(), OperatorTransform()])
app.layout = html.Div([html.Button(k, id=f"btn_{k}") for k in gui_actions] + [
    dcc.Store(id="store", data=[]),
    html.Div(id="log"),
])

for k in gui_actions:
    app.callback(OperatorOutput("store", "data"), Input(f"btn_{k}", "n_clicks"))(gui_actions[k])


@app.callback(Output("log", "children"), Input("store", "data"))
def update_log(data):
    return json.dumps(data)


if __name__ == '__main__':
    app.run_server()
