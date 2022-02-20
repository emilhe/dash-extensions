import examples.pages.module as module
import examples.pages.app as sub_app
import dash_bootstrap_components as dbc

from dash import dcc, html
from dash_extensions.enrich import DashProxy, Input, Output
from dash_extensions.multipage import PageCollection, app_to_page, module_to_page, Page, CONTENT_ID, URL_ID


# region Page definition in current module


def layout(*args, **kwargs):
    return dbc.Container(
        [
            dbc.Row(html.Br()),
            dbc.Row(dcc.Input(id="input"), justify="around"),
            dbc.Row(html.Div(id="output"), justify="around"),
        ],
        fluid=True,
    )


def callbacks(app):
    @app.callback(Output("output", "children"), [Input("input", "value")])
    def hello(value):
        return f"PAGE says: Hello {value}!"


page = Page(id="page", label="A page", layout=layout, callbacks=callbacks)


# endregion


def simple_menu(page_collection):
    children = []
    pages = page_collection.pages
    for i, page in enumerate(pages):
        children.append(html.A(children=page.label, href="/{}".format(page.id)))
        if i < (len(pages) - 1):
            children.append(html.Br())
    return children


# Create pages.
pc = PageCollection(
    pages=[
        page,  # page defined in current module
        module_to_page(module, "module", "A module"),  # page defined in another module
        app_to_page(sub_app.app, "app", "An app"),  # app loaded as a page
    ]
)
# Create app.
app = DashProxy(suppress_callback_exceptions=True)
app.layout = html.Div(simple_menu(pc) + [html.Div(id=CONTENT_ID), dcc.Location(id=URL_ID)])
# Register callbacks.
pc.navigation(app)
pc.callbacks(app)

if __name__ == "__main__":
    app.run_server()
