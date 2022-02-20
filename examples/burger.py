import dash_html_components as html
from dash import Dash
from dash_extensions import Burger


def link_element(icon, text):
    return html.A(
        children=[html.I(className=icon), html.Span(text)],
        href=f"/{text}",
        className="bm-item",
        style={"display": "block"},
    )


# Example CSS from the original demo.
external_css = [
    "https://negomi.github.io/react-burger-menu/example.css",
    "https://negomi.github.io/react-burger-menu/normalize.css",
    "https://negomi.github.io/react-burger-menu/fonts/font-awesome-4.2.0/css/font-awesome.min.css",
]
# Create example app.
app = Dash(external_stylesheets=external_css)
app.layout = html.Div(
    [
        Burger(
            children=[
                html.Nav(
                    children=[
                        link_element("fa fa-fw fa-star-o", "Favorites"),
                        link_element("fa fa-fw fa-bell-o", "Alerts"),
                        link_element("fa fa-fw fa-envelope-o", "Messages"),
                        link_element("fa fa-fw fa-comment-o", "Comments"),
                        link_element("fa fa-fw fa-bar-chart-o", "Analytics"),
                        link_element("fa fa-fw fa-newspaper-o", "Reading List"),
                    ],
                    className="bm-item-list",
                    style={"height": "100%"},
                )
            ],
            id="slide",
        ),
        html.Main("Hello world!", style={"width": "100%", "height": "100vh"}, id="main"),
    ],
    id="outer-container",
    style={"height": "100%"},
)

if __name__ == "__main__":
    app.run_server()
