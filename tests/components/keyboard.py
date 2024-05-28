from dash import Dash

from dash_extensions import Keyboard

app = Dash()
app.layout = Keyboard()

if __name__ == "__main__":
    app.run_server(port=9999)
