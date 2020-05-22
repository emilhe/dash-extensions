import uuid
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Output, Input


def fix_page_load_anchor_issue(app, delay=None):
    """
    Fixes the issue that the pages is not scrolled to the anchor position on initial load.
    :param app: the Dash app object
    :param delay: in some cases, an additional delay might be needed for the page to load, specify in ms
    :return: dummy elements, which must be added to the layout for the fix to work
    """
    # Create dummy components.
    input_id, output_id = str(uuid.uuid4()), str(uuid.uuid4())
    dummy_input = html.Div(id=input_id, style={"display": "hidden"})
    dummy_output = html.Div(id=output_id, style={"display": "hidden"})
    # Setup the callback that does the magic.
    app.clientside_callback(
        """
        function(dummy_value) {{
            setTimeout(function(){{
                const match = document.getElementById(window.location.hash.substring(1))
                match.scrollIntoView();
            }}, {});
        }}
        """.format(delay),
        Output(output_id, "children"), [Input(input_id, "children")], prevent_initial_call=False)
    return [dummy_input, dummy_output]