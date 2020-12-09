import examples.pages.page as page
import examples.pages.app as sub_app
import dash_html_components as html
from dash_extensions.enrich import DashProxy
from multipage import PageCollection, make_burger, app_to_page, module_to_page, default_layout

URL_ID = "url"
CONTENT_ID = "content"
# Create pages.
pc = PageCollection(pages=[
    module_to_page(page, "page", "A page"),
    app_to_page(sub_app.app, "app", "An app")
])
# Create app.
app = DashProxy()
app.layout = html.Div([make_burger(pc, effect="slide", position="right"), default_layout()])
# Register callbacks.
pc.navigation(app, CONTENT_ID, URL_ID)
pc.callbacks(app)

if __name__ == '__main__':
    app.run_server()
