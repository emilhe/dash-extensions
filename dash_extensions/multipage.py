import dash_html_components as html

from dash.exceptions import PreventUpdate
from .enrich import Output, Input
from .Burger import Burger

URL_ID = "url"
CONTENT_ID = "content"


class Page:
    def __init__(self, id, label, layout=None):
        self.id = id
        self.label = label
        self.layout = layout



class PageCollection:
    def __init__(self, pages, default_page=None, is_authorized=None, unauthorized=None):
        self.pages = pages
        self.is_authorized = is_authorized
        self.unauthorized = html.Div("Unauthorized.") if unauthorized is None else unauthorized
        self.default_page = default_page if default_page is not None else pages[0]

    def navigate_to(self, path, *args, **kwargs):
        if path is None:
            raise PreventUpdate
        # Locate the page. Maybe make this is more advanced later, for now just snap the id.
        page_ids = [page.id for page in self.pages]
        next_page = self.default_page
        if path is not None:
            page_id = path[1:]
            if page_id in page_ids:
                next_page = page_id
        # TODO: Is this necessary?
        # # Check that the user is authorized.
        # if self.is_authorized is not None:
        #     if not self.is_authorized(next_page):
        #         return self.unauthorized
        # At this point, the user is authorized, so the page can safely be rendered.
        return self.pages[page_ids.index(next_page)].layout(path, *args, **kwargs)

    def register_navigation(self, app, content_id=CONTENT_ID, url_id=URL_ID):
        @app.callback(Output(content_id, "children"), [Input(url_id, "pathname")])
        def navigate_to(path):
            return self.navigate_to(path)

    def register_modules(self, app):
        for page in self.pages:
            if page.module is None:
                continue
            page.module.register(app)


# region Menus

def make_burger(pages, before_pages=None, after_pages=None, href=None, **kwargs):
    children = []
    for i, page in enumerate(pages):
        children.append(html.A(children=page.label, href=href(page) if href is not None else "/{}".format(page.id)))
        if i < (len(pages) - 1):
            children.append(html.Br())
    children = before_pages + children if before_pages is not None else children
    children = children + after_pages if after_pages is not None else children
    return Burger(children=children, **kwargs)


# endregion

# region App to page

def apply_prefix(prefix, component_id):
    if isinstance(component_id, dict):
        # TODO: Handle wild cards.
        # for key in component_id:
        #     if key == "index":
        #         continue
        #     component_id[key] = "{}-{}".format(prefix, component_id[key])
        return component_id
    return "{}-{}".format(prefix, component_id)


def prefix_id(arg, key):
    if hasattr(arg, 'component_id'):
        arg.component_id = apply_prefix(key, arg.component_id)
    if hasattr(arg, '__len__'):
        for entry in arg:
            entry.component_id = apply_prefix(key, entry.component_id)


def prefix_id_recursively(item, key):
    if hasattr(item, "id"):
        item.id = apply_prefix(key, item.id)
    if hasattr(item, "children"):
        children = item.children
        if hasattr(children, "id"):
            children.id = apply_prefix(key, children.id)
        if hasattr(children, "__len__"):
            for child in children:
                prefix_id_recursively(child, key)

def app_to_page(app, id):

def build_layout(app, wd, key):
    # Proxy that attaches callback to main app (with prefix).
    class AppProxy:

        def __init__(self, external_stylesheets=None, *args, **kwargs):
            self.layout = None
            self.external_stylesheets = external_stylesheets

        def callback(self, *args):
            for arg in list(args):
                prefix_id(arg, key)
            return app.callback(*args)

        @property
        def server(self):
            return app.server

        @property
        def index_string(self):
            return app.index_string

        @index_string.setter
        def index_string(self, value):
            app.index_string = value

    # Apply temporary monkey patch.
    dash_real = dash.Dash
    dash.Dash = AppProxy
    mod = importlib.import_module(f'{wd}.{key}')
    example = getattr(mod, "app")
    prefix_id_recursively(example.layout, key)
    app_layouts[key] = example.layout
    dash.Dash = dash_real

    return example.external_stylesheets

# endregion
