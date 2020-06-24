import io
import ntpath
import base64
import uuid
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Output, Input


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


_writer_binary_map = {
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


def send_data_frame(df_writer, filename, binary=None, mime_type=None):
    """
    Convert a pandas data frame into the format expected by the Download component.
    :param df_writer: a writer that can write the df to a StringIO (if binary=False) or a BytesIO (if binary=True)
    :param filename: the name of the file
    :param binary: if False, the writer is provided with StringIO, if True a BytesIO. Per default, pandas writers are
    handles automatically, for custom writers the default is False
    :param mime_type: mime type of the file (optional, passed to Blob in the javascript layer)
    :return: dict of data frame content (base64 encoded) and meta data used by the Download component

    Examples
    --------

    >>> df = pd.DataFrame({'a': [1, 2, 3, 4], 'b': [2, 1, 5, 6], 'c': ['x', 'x', 'y', 'y']})
    ...
    >>> send_data_frame(df.to_csv, "mydf.csv")  # download as csv
    >>> send_data_frame(df.to_json, "mydf.json")  # download as json
    >>> send_data_frame(df.to_excel, "mydf.xls", binary=True) # download as excel
    >>> send_data_frame(df.to_pkl, "mydf.pkl", binary=True) # download as pickle

    """
    # Try to guess what IO is needed (will work for standard pandas writers).
    if binary is None:
        name = df_writer.__name__
        if name in _writer_binary_map.keys():
            binary = _writer_binary_map[name]
    # Create data IO.
    data_io = io.BytesIO() if binary else io.StringIO()
    # Some pandas writers try to close the IO, we do not want that.
    data_io_close = data_io.close
    data_io.close = lambda: None
    # Write data frame content to base64 string.
    df_writer(data_io)
    data_value = data_io.getvalue() if binary else data_io.getvalue().encode()
    data_io_close()
    content = base64.b64encode(data_value).decode()
    # Wrap in dict.
    return dict(content=content, filename=filename, mime_type=mime_type, base64=True)



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
