import pytest
from dash.testing.application_runners import import_app

# All custom dash components.
components = ["before_after", "defer_script", "event_listener", "event_source", "keyboard", "lottie", "mermaid",
              "purify", "ticker", "websocket"]


# Basic test for the component rendering.
@pytest.mark.parametrize("component", components)
def test_render_components(dash_duo, component):
    # Start a dash app contained as the variable `app` in `usage.py`
    app = import_app(f"component_examples.{component}")
    dash_duo.start_server(app)
