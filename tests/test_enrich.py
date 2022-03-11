from enrich import DashBlueprint, Output, Input, State, CallbackBlueprint, html, DashProxy
from dash import Dash


def test_callback_blueprint():
    # Test single element.
    cbp = CallbackBlueprint(State("s", "prop"), Output("o", "prop"), Input("i", "prop"))
    assert cbp.outputs == [Output("o", "prop")]
    assert cbp.inputs == [State("s", "prop"), Input("i", "prop")]
    # Test list element.
    cbp = CallbackBlueprint(
        [State("s", "prop"), State("s2", "prop")],
        [Output("o", "prop")],
        [Input("i", "prop")]
    )
    assert cbp.outputs == [Output("o", "prop")]
    assert cbp.inputs == [State("s", "prop"), State("s2", "prop"), Input("i", "prop")]
    # Test mix.
    cbp = CallbackBlueprint(
        [State("s", "prop"), State("s2", "prop")],
        Input("i0", "prop"),
        [Output("o", "prop")],
        State("s3", "prop"),
        [Input("i", "prop")],
        Output("o2", "prop")
    )
    assert cbp.outputs == [Output("o", "prop"), Output("o2", "prop")]
    assert cbp.inputs == [State("s", "prop"), State("s2", "prop"), Input("i0", "prop"),
                          State("s3", "prop"), Input("i", "prop")]
    # Test variables.
    my_input = html.Button()
    my_output = html.Div()
    cbp = CallbackBlueprint(
        Input(my_input, "n_clicks"),
        Output(my_output, "children")
    )
    assert cbp.outputs == [Output(my_output, "children")]
    assert cbp.inputs == [Input(my_input, "n_clicks")]
    # Test kwargs.
    cbp = CallbackBlueprint(
        Input(my_input, "n_clicks"),
        Output(my_output, "children"),
        hello="world"
    )
    assert cbp.kwargs == dict(hello="world")


def test_dash_proxy(dash_duo):
    app = Dash()
    app.layout = html.Div([
        html.Button(id="btn"),
        html.Div(id="log")
    ])

    @app.callback(Output("log", "children"), Input("btn", "n_clicks"))
    def update_log(n_clicks):
        return n_clicks

    dash_duo.start_server(app)
    a = dash_duo.find_element("#log")
    # assert dash_duo.find_element("div").children == ""
    # dash_duo.find_element("#btn").click()


def test_parse_callbacks():
    output_test, input_test, state_test = Output("x", "prop"), Input("y", "prop"), State("z", "prop")
    kwargs = dict(hello="world")
    callback_result = "result"
    expected = {Output: [output_test], Input: [input_test], State: [state_test], 'kwargs': kwargs,
                'multi_output': False, 'sorted_args': [output_test, input_test, state_test], "f": callback_result}

    # Single element syntax.

    dbp = DashBlueprint()

    @dbp.callback(output_test, input_test, state_test, **kwargs)
    def callback():
        return callback_result

    cb = dbp.callbacks[0]
    cb["f"] = cb["f"]()
    assert expected == dbp.callbacks[0]

    # List syntax

    dbp = DashBlueprint()

    @dbp.callback([output_test], [input_test], [state_test], **kwargs)
    def callback():
        return callback_result

    cb = dbp.callbacks[0]
    cb["f"] = cb["f"]()
    assert expected == dbp.callbacks[0]

    # Mixed syntax

    dbp = DashBlueprint()

    @dbp.callback([output_test], input_test, [state_test], **kwargs)
    def callback():
        return callback_result

    cb = dbp.callbacks[0]
    cb["f"] = cb["f"]()
    assert expected == dbp.callbacks[0]
