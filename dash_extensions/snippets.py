import io
import json
import ntpath
import base64
import uuid

import dash
import dash_html_components as html

from dash.dependencies import Output, Input


# region JavaScript binding stuff

class JavaScriptNamespace:
    def __init__(self, *args):
        self.args = list(args)

    def __call__(self, variable):
        return js_variable(self.args + [variable])


def js_arrow_function(value):
    return dict(arrow=value)


def js_variable(*args):
    return dict(variable=".".join(list(args)))


# endregion

# region Utils for Download component


def send_file(path, filename=None, mime_type=None):
    """
    Convert a file into the format expected by the Download component.
    :param path: path to the file to be sent
    :param filename: name of the file, if not provided the original filename is used
    :param mime_type: mime type of the file (optional, passed to Blob in the javascript layer)
    :return: dict of file content (base64 encoded) and meta data used by the Download component
    """
    # If filename is not set, read it from the path.
    if filename is None:
        filename = ntpath.basename(path)
    # Read the file into a base64 string.
    with open(path, 'rb') as f:
        content = base64.b64encode(f.read()).decode()
    # Wrap in dict.
    return dict(content=content, filename=filename, mime_type=mime_type, base64=True)


def send_bytes(writer, filename, mime_type=None, **kwargs):
    """
    Convert data written to BytesIO into the format expected by the Download component.
    :param writer: a writer that can write to BytesIO
    :param filename: the name of the file
    :param mime_type: mime type of the file (optional, passed to Blob in the javascript layer)
    :return: dict of data frame content (base64 encoded) and meta data used by the Download component
    """
    data_io = io.BytesIO()
    # Some pandas writers try to close the IO, we do not want that.
    data_io_close = data_io.close
    data_io.close = lambda: None
    # Write data content to base64 string.
    writer(data_io, **kwargs)
    data_value = data_io.getvalue()
    data_io_close()
    content = base64.b64encode(data_value).decode()
    # Wrap in dict.
    return dict(content=content, filename=filename, mime_type=mime_type, base64=True)


def send_string(writer, filename, mime_type=None, **kwargs):
    """
    Convert data written to StringIO into the format expected by the Download component.
    :param writer: a writer that can write to StringIO
    :param filename: the name of the file
    :param mime_type: mime type of the file (optional, passed to Blob in the javascript layer)
    :return: dict of data frame content (base64 encoded) and meta data used by the Download component
    """
    data_io = io.StringIO()
    # Some pandas writers try to close the IO, we do not want that.
    data_io_close = data_io.close
    data_io.close = lambda: None
    # Write data content to base64 string.
    writer(data_io, **kwargs)
    data_value = data_io.getvalue().encode()
    data_io_close()
    content = base64.b64encode(data_value).decode()
    # Wrap in dict.
    return dict(content=content, filename=filename, mime_type=mime_type, base64=True)


known_pandas_writers = {
    "to_csv": False,
    "to_json": False,
    "to_html": False,
    "to_excel": True,
    "to_hdf": True,
    "to_feather": True,
    "to_parquet": True,
    "to_msgpack": True,
    "to_stata": True,
    "to_pickle": True,
}


def send_data_frame(writer, filename, mime_type=None, **kwargs):
    """
    Convert data frame into the format expected by the Download component.
    :param writer: a data frame writer
    :param filename: the name of the file
    :param mime_type: mime type of the file (optional, passed to Blob in the javascript layer)
    :return: dict of data frame content (base64 encoded) and meta data used by the Download component

    Examples
    --------

    >>> df = pd.DataFrame({'a': [1, 2, 3, 4], 'b': [2, 1, 5, 6], 'c': ['x', 'x', 'y', 'y']})
    ...
    >>> send_data_frame(df.to_csv, "mydf.csv")  # download as csv
    >>> send_data_frame(df.to_json, "mydf.json")  # download as json
    >>> send_data_frame(df.to_excel, "mydf.xls", index=False) # download as excel
    >>> send_data_frame(df.to_pkl, "mydf.pkl") # download as pickle

    """
    name = writer.__name__
    # Check if the provided writer is known.
    if name not in known_pandas_writers.keys():
        raise ValueError("The provided writer ({}) is not supported, "
                         "try calling send_string or send_bytes directly.".format(name))
    # If binary, use send_bytes.
    if known_pandas_writers[name]:
        return send_bytes(writer, filename, mime_type, **kwargs)
    # Otherwise, use send_string.
    return send_string(writer, filename, mime_type, **kwargs)


# endregion

# region Get triggered


class Triggered(object):
    def __init__(self, id, **kwargs):
        self.id = id
        for key in kwargs:
            setattr(self, key, kwargs[key])


def get_triggered():
    triggered = dash.callback_context.triggered
    if not triggered:
        return Triggered(None)
    # Collect trigger ids and values.
    triggered_id = None
    triggered_values = {}
    for entry in triggered:
        # TODO: Test this part.
        elements = entry['prop_id'].split(".")
        current_id = ".".join(elements[:-1])
        current_prop = elements[-1]
        # Determine the trigger object.
        if triggered_id is None:
            triggered_id = current_id
        # TODO: Should all properties of the trigger be registered, or only one?
        if triggered_id != current_id:
            continue
        triggered_values[current_prop] = entry['value']
    # Now, create an object.
    try:
        triggered_id = json.loads(triggered_id)
    except ValueError:
        pass
    return Triggered(triggered_id, **triggered_values)


# endregion

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
