import examples.pages.module as module
import examples.pages.app as sub_app
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Input, Output
from dash_extensions.enrich import DashProxy
from multipage import PageCollection, make_burger, app_to_page, module_to_page, default_layout, Page


def layout(*args, **kwargs):
    return dbc.Container([
        dbc.Row(html.Br()),
        dbc.Row(dcc.Input(id="input"), justify="around"),
        dbc.Row(html.Div(id="output"), justify="around"),
    ], fluid=True)


def callbacks(app):
    @app.callback(Output("output", "children"), [Input("input", "value")])
    def hello(value):
        return f"PAGE says: Hello {value}!"


# Create pages.
pc = PageCollection(pages=[
    Page(id="page", label="A page", layout=layout, callbacks=callbacks),
    module_to_page(module, "module", "A module"),
    app_to_page(sub_app.app, "app", "An app")
])
# Create app.
app = DashProxy(suppress_callback_exceptions=True)
app.layout = html.Div([make_burger(pc, effect="slide", position="right"), default_layout()])
# Register callbacks.
pc.navigation(app)
pc.callbacks(app)

if __name__ == '__main__':
    app.run_server(debug=False)
