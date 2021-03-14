import dash_html_components as html
from dash_extensions.enrich import Output, DashProxy, Input, MultiplexerTransform

n = 10
# Create example app with n buttons.
buttons = [html.Button(f"Button {i}", id=f"btn_{i}") for i in range(n)]
app = DashProxy(prevent_initial_callbacks=True, transforms=[MultiplexerTransform()])
app.layout = html.Div(buttons + [html.Div(id="log")])
# Target the same output n times.
for button in buttons:
    app.callback(Output("log", "children"), Input(button.id, "n_clicks"))(lambda _, x=button.id: f"Your clicked {x}!")

if __name__ == '__main__':
    app.run_server(debug=True)
