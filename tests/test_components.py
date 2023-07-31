import pytest
from dash.testing.application_runners import import_app

# All custom dash components.
components = ["before_after", "defer_script", "event_listener", "lottie", "mermaid", "purify"]


# Basic test for the component rendering.
@pytest.mark.parametrize("component", components)
def test_render_components(dash_duo, component):
    app = import_app(f"tests.components.{component}"), "ticker"
    dash_duo.start_server(app)
