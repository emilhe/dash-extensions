from enrich import DashBlueprint, Output, Input, State, CallbackBlueprint, html, DashProxy, NoOutputTransform, Trigger, \
    TriggerTransform, MultiplexerTransform


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
    app = DashProxy()
    app.layout = html.Div([
        html.Button(id="btn"),
        html.Div(id="log_server"),
        html.Div(id="log_client")
    ])
    app.clientside_callback("function(x){return x;}",
                            Output("log_client", "children"), Input("btn", "n_clicks"))

    @app.callback(Output("log_server", "children"), Input("btn", "n_clicks"))
    def update_log(n_clicks):
        return n_clicks

    dash_duo.start_server(app)
    log_server = dash_duo.find_element("#log_server")
    log_client = dash_duo.find_element("#log_client")
    assert log_server.text == ""
    assert log_client.text == ""
    dash_duo.find_element("#btn").click()
    assert log_server.text == "1"
    assert log_client.text == "1"


def test_no_output_transform(dash_duo):
    app = DashProxy()
    app.layout = html.Div([
        html.Button(id="btn"),
    ])

    @app.callback(Input("btn", "n_clicks"))
    def update(n_clicks):
        return n_clicks

    # Check that the callback doesn't have an output.
    callbacks, _ = app.blueprint._resolve_callbacks()
    assert len(callbacks[0].outputs) == 0
    # Check that the transform fixes it.
    app.blueprint.transforms.append(NoOutputTransform())
    callbacks, _ = app.blueprint._resolve_callbacks()
    assert len(callbacks[0].outputs) == 1
    # Finally, check that the app works.
    dash_duo.start_server(app)
    dash_duo.find_element("#btn").click()


def test_trigger_transform(dash_duo):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[TriggerTransform()])
    app.layout = html.Div([
        html.Button(id="btn1"),
        html.Button(id="btn2"),
        html.Button(id="btn3"),
        html.Button(id="btn4"),
        html.Div(id="log"),
    ])

    @app.callback(Output("log", "children"),
                  Trigger("btn1", "n_clicks"),
                  Input("btn2", "n_clicks"),
                  Trigger("btn3", "n_clicks"),
                  State("btn4", "n_clicks"))
    def update(n_clicks2, n_clicks4):
        return f"{str(n_clicks2)}-{str(n_clicks4)}"

    # Check that the app works.
    dash_duo.start_server(app)
    log = dash_duo.find_element("#log")
    assert log.text == ""
    dash_duo.find_element("#btn1").click()
    assert log.text == "None-None"
    dash_duo.find_element("#btn2").click()
    assert log.text == "1-None"
    dash_duo.find_element("#btn4").click()
    assert log.text == "1-None"
    dash_duo.find_element("#btn3").click()
    assert log.text == "1-1"


def test_multiplexer_transform(dash_duo):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[MultiplexerTransform()])
    app.layout = html.Div([
        html.Button(id="left"),
        html.Button(id="right"),
        html.Div(id="log"),
    ])

    @app.callback(Output("log", "children"), Input("left", "n_clicks"))
    def update_left(_):
        return "left"

    @app.callback(Output("log", "children"), Input("right", "n_clicks"))
    def update_right(_):
        return "right"

    # Check that the app works.
    dash_duo.start_server(app)
    log = dash_duo.find_element("#log")
    assert log.text == ""
    dash_duo.find_element("#left").click()
    dash_duo.wait_for_text_to_equal("#log", "left", timeout=0.1)
    assert log.text == "left"
    dash_duo.find_element("#right").click()
    dash_duo.wait_for_text_to_equal("#log", "right", timeout=0.1)
    assert log.text == "right"


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
