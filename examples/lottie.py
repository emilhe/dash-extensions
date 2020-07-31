import dash
import dash_html_components as html
import dash_extensions as de

# Setup options.
url = "https://assets9.lottiefiles.com/packages/lf20_YXD37q.json"
options = dict(loop=True, autoplay=True, rendererSettings=dict(preserveAspectRatio='xMidYMid slice'))
# Create example app.
app = dash.Dash(__name__)
app.layout = html.Div(de.Lottie(options=options, width="25%", height="25%", url=url))

if __name__ == '__main__':
    app.run_server()