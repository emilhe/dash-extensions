from dash import Dash, html
from dash_iconify import DashIconify

from dash_extensions import PassComponentDemo

app = Dash(__name__)
app.layout = html.Div(
    [
        PassComponentDemo(
            components=[
                DashIconify(icon="ion:logo-github", width=30, rotate=1, flip="horizontal"),
            ],
        ),
    ]
)

if __name__ == "__main__":
    app.run(debug=False)
