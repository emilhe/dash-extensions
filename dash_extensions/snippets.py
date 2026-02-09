import json
from typing import Any, List, Sequence, Union

from dash import Input, Output, callback_context, html

Component = Any

# region Get triggered


class Triggered(object):
    def __init__(self, id, **kwargs):
        self.id = id
        for key in kwargs:
            setattr(self, key, kwargs[key])


def get_triggered() -> Triggered:  # noqa: C901
    triggered = callback_context.triggered
    if not triggered:
        return Triggered(None)
    # Collect trigger ids and values.
    triggered_id = None
    triggered_values = {}
    for entry in triggered:
        # TODO: Test this part.
        elements = entry["prop_id"].split(".")
        current_id = ".".join(elements[:-1])
        current_prop = elements[-1]
        # Determine the trigger object.
        if triggered_id is None:
            triggered_id = current_id
        # TODO: Should all properties of the trigger be registered, or only one?
        if triggered_id != current_id:
            continue
        triggered_values[current_prop] = entry["value"]
    # Now, create an object.
    try:
        triggered_id = json.loads(triggered_id) if triggered_id is not None else None
    except ValueError:
        pass
    return Triggered(triggered_id, **triggered_values)


# endregion

# region Utils for html tables

Node = Union[str, float, int, Component]


def generate_html_table(
    columns: List[Node],
    rows: List[List[Node]] | None = None,
    footers: List[Node] | None = None,
    caption: Node | None = None,
) -> Sequence[Component]:
    rows = [] if rows is None else rows
    # Create table structure.
    html_header = [html.Tr([html.Th(col) for col in columns])]
    html_rows = [html.Tr([html.Td(children=cell) for cell in row]) for row in rows]
    html_table = [html.Thead(html_header), html.Tbody(html_rows)]
    # Add (optional) caption.
    if caption is not None:
        html_table = [html.Caption(caption)] + html_table
    # Add (optional) footer.
    if footers is not None:
        html_footer = [html.Tr([html.Th(col) for col in footers])]
        html_table += html.Tfoot(html_footer)
    return html_table


# endregion


def fix_page_load_anchor_issue(app, delay, input_id=None, output_id=None):
    """
    Fixes the issue that the pages is not scrolled to the anchor position on initial load.
    :param app: the Dash app object
    :param delay: in some cases, an additional delay might be needed for the page to load, specify in ms
    :param input_id: id of input dummy element
    :param output_id: id of output dummy element
    :return: dummy elements, which must be added to the layout for the fix to work
    """
    # Create dummy components.
    input_id = input_id if input_id is not None else "fix_page_load_anchor_issue_input"
    output_id = output_id if output_id is not None else "fix_page_load_anchor_issue_output"
    dummy_input = html.Div(id=input_id, style={"display": "hidden"})
    dummy_output = html.Div(id=output_id, style={"display": "hidden"})
    # Setup the callback that does the magic.
    app.clientside_callback(
        """
        function(dummy_value) {{
            setTimeout(function(){{
                const match = document.getElementById(window.location.hash.substring(1))
                if (match) {{
                    match.scrollIntoView();
                }}
            }}, {});
        }}
        """.format(delay),
        Output(output_id, "children"),
        [Input(input_id, "children")],
        prevent_initial_call=False,
    )
    return [dummy_input, dummy_output]
