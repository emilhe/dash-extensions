from dash_extensions.enrich import DashProxy, MultiplexerTransform, Input, Output, ALL
import dash_html_components as html


def make_callback(i):
    @app.callback(Output({'type': 'div', 'id': ALL}, 'children'), Input({'type': f'button{i}', 'id': ALL}, 'n_clicks'))
    def func(n):
        return [f"Hello from group {i}"] * len(n)


def make_block(i):
    layout = [
        html.Button(f"Button 0 in group {i}", id={'type': f'button{i}', 'id': 0}),
        html.Button(f"Button 1 in group {i}", id={'type': f'button{i}', 'id': 1}),
        html.Div(f"Div {i}", id={'type': f'div', 'id': i}),
    ]
    make_callback(i)
    return layout


app = DashProxy(transforms=[MultiplexerTransform()], prevent_initial_callbacks=True)
app.layout = html.Div(make_block(0) + make_block(1))

if __name__ == '__main__':
    app.run_server(port=7778, debug=True)
