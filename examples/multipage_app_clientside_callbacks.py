import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash_extensions.enrich import DashProxy
from dash_extensions.multipage import PageCollection, Page, CONTENT_ID, URL_ID


def layout(*args, **kwargs):
    return html.Div([
        dcc.Input(id="input"),
        html.Div(id="output"),
        html.P(
            [html.Span("The current date is: ", id="date-text"), html.Span(id="date")],
            style={"textAlign": "center"},
        )
    ])


def callbacks(app):
    @app.callback(Output("output", "children"), [Input("input", "value")])
    def hello(value):
        return f"PAGE says: Hello {value}!"

    app.clientside_callback(
        """
        function(_) {
            return Date().toLocaleString();
        }
        """,
        Output('date', 'children'),
        Input('date-text', 'children')
    )


pc = PageCollection(pages=[
    Page(id="page", label="A page", layout=layout, callbacks=callbacks)
])
app = DashProxy(suppress_callback_exceptions=True)
app.layout = html.Div([html.Div(id=CONTENT_ID), dcc.Location(id=URL_ID)])
pc.navigation(app)
pc.callbacks(app)


if __name__ == '__main__':
    app.run_server(debug=True)

