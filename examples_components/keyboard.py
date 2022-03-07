import json
from dash import html, Output, Input, Dash
from dash_extensions import Keyboard

# Create small example app.
app = Dash()
app.layout = html.Div([Keyboard(id="keyboard"), html.Div(id="output")])


@app.callback(
    Output("output", "children"),
    [
        Input("keyboard", "keydown"),
        Input("keyboard", "n_keydowns"),
        Input("keyboard", "keyup"),
        Input("keyboard", "n_keyups"),
        Input("keyboard", "keys_pressed"),
    ],
)
def keydown(keydown, n_keydowns, keyup, n_keyups, keys_pressed):
    print(keys_pressed)
    return f"{json.dumps(keydown)}\n{n_keydowns}\n{keyup}\n{n_keyups}\n{keys_pressed}"


if __name__ == "__main__":
    app.run_server()