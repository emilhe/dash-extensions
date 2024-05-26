from dash_extensions.enrich import Dash, Input, Output, callback, ctx, html

app = Dash(__name__)
app.layout = html.Div(
    [
        html.Button("Button 1", id="btn-1"),
        html.Button("Button 2", id="btn-2"),
        html.Button("Button 3", id="btn-3"),
        html.Div(id="container"),
        html.Div(id="container-no-ctx"),
    ]
)


@callback(Output("container-no-ctx", "children"), Input("btn-1", "n_clicks"), Input("btn-2", "n_clicks"))
def update(btn1, btn2):
    return f"button 1: {btn1} & button 2: {btn2}"


@callback(
    Output("container", "children"), Input("btn-1", "n_clicks"), Input("btn-2", "n_clicks"), Input("btn-3", "n_clicks")
)
def display(btn1, btn2, btn3):
    button_clicked = ctx.triggered_id
    return f"You last clicked button with ID {button_clicked}"


if __name__ == "__main__":
    app.run_server(debug=True)
