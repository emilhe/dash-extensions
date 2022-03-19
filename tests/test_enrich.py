import time
import pandas as pd

from dash_extensions.enrich import Output, Input, State, CallbackBlueprint, html, DashProxy, NoOutputTransform, Trigger, \
    TriggerTransform, MultiplexerTransform, PrefixIdTransform, callback, clientside_callback, DashLogger, LogTransform, \
    BlockingCallbackTransform, dcc, ServersideOutputTransform, ServersideOutput, ALL, FileSystemStore


# region Test utils/stubs

def _get_basic_dash_proxy(**kwargs) -> DashProxy:
    app = DashProxy(**kwargs)
    app.layout = html.Div([
        html.Button(id="btn"),
        html.Div(id="log_server"),
        html.Div(id="log_client")
    ])
    return app


def _bind_basic_callback(app):
    @app.callback(Output("log_server", "children"), Input("btn", "n_clicks"))
    def update_log(n_clicks):
        return n_clicks


def _bind_basic_clientside_callback(app):
    app.clientside_callback("function(x){return x;}",
                            Output("log_client", "children"), Input("btn", "n_clicks"))


def _basic_dash_proxy_test(dash_duo, app, element_ids=None, btn_id="btn"):
    element_ids = ["log_server", "log_client"] if element_ids is None else element_ids
    dash_duo.start_server(app)
    elements = [dash_duo.find_element(f"#{element_id}") for element_id in element_ids]
    for element in elements:
        assert element.text == ""
    dash_duo.find_element(f"#{btn_id}").click()
    time.sleep(0.1)
    for element in elements:
        assert element.text == "1"


# endregion

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
    app = _get_basic_dash_proxy()
    _bind_basic_callback(app)
    _bind_basic_clientside_callback(app)
    # Check that both server and client side callbacks work.
    _basic_dash_proxy_test(dash_duo, app)


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
    time.sleep(0.1)
    assert log.text == "None-None"
    dash_duo.find_element("#btn2").click()
    time.sleep(0.1)
    assert log.text == "1-None"
    dash_duo.find_element("#btn4").click()
    time.sleep(0.1)
    assert log.text == "1-None"
    dash_duo.find_element("#btn3").click()
    time.sleep(0.1)
    assert log.text == "1-1"


def test_multiplexer_transform(dash_duo):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[MultiplexerTransform()])
    app.layout = html.Div([
        html.Button(id="left"),
        html.Button(id="right"),
        html.Div(id="log"),
    ])
    app.clientside_callback("function(x){return 'left'}", Output("log", "children"), Input("left", "n_clicks"))

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


def test_multiplexer_transform_wildcard(dash_duo):
    def make_callback(i):
        @app.callback(Output({"type": "div", "id": ALL}, "children"),
                      Input({"type": f"button{i}", "id": ALL}, "n_clicks"))
        def func(n):
            return [f"Hello from group {i}"] * len(n)

    def make_block(i):
        layout = [
            html.Button(f"Button 0 in group {i}", id={"type": f"button{i}", "id": "x"}),
            html.Button(f"Button 1 in group {i}", id={"type": f"button{i}", "id": "y"}),
            html.Div(f"Div {i}", id={"type": f"div", "id": i}),
        ]
        make_callback(i)
        return layout

    app = DashProxy(transforms=[MultiplexerTransform()], prevent_initial_callbacks=True)
    app.layout = html.Div(make_block("0") + make_block("1"))

    def cssid(**kwargs):
        # escaped CSS for object IDs
        kvs = r"\,".join([r"\"" + k + r"\"\:\"" + kwargs[k] + r"\"" for k in kwargs])
        return r"#\{" + kvs + r"\}"

    dash_duo.start_server(app)
    dash_duo.find_element(cssid(id="x", type="button0")).click()
    assert dash_duo.find_element(cssid(id="0", type="div")).text == "Hello from group 0"
    dash_duo.find_element(cssid(id="y", type="button1")).click()
    assert dash_duo.find_element(cssid(id="1", type="div")).text == "Hello from group 1"


def test_prefix_id_transform(dash_duo):
    app = _get_basic_dash_proxy(transforms=[PrefixIdTransform(prefix="x")])
    _bind_basic_callback(app)
    _bind_basic_clientside_callback(app)
    # Check that both server and client side callbacks work.
    _basic_dash_proxy_test(dash_duo, app, ["x-log_server", "x-log_client"], "x-btn")


def test_global_blueprint(dash_duo):
    app = _get_basic_dash_proxy()
    clientside_callback("function(x){return x;}",
                        Output("log_client", "children"), Input("btn", "n_clicks"))

    @callback(Output("log_server", "children"), Input("btn", "n_clicks"))
    def update_log(n_clicks):
        return n_clicks

    # Check that callbacks work.
    _basic_dash_proxy_test(dash_duo, app)


def test_blocking_callback_transform(dash_duo):
    app = DashProxy(transforms=[BlockingCallbackTransform(timeout=5)])
    app.layout = html.Div([html.Div(id="log"), dcc.Interval(id="trigger", interval=500)])
    msg = "Hello world!"

    @app.callback(Output("log", "children"), Input("trigger", "n_intervals"), blocking=True)
    def update(_):
        time.sleep(1)
        return msg

    # Check that stuff works. It doesn't using a normal Dash object.
    dash_duo.start_server(app)
    dash_duo.wait_for_text_to_equal("#log", msg, timeout=5)
    assert dash_duo.find_element("#log").text == msg


def test_serverside_output_transform(dash_duo):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[ServersideOutputTransform()])
    app.layout = html.Div([
        html.Button(id="btn"),
        html.Div(id="store"),
        html.Div(id="log"),
    ])

    @app.callback(ServersideOutput("store", "children"), Input("btn", "n_clicks"))
    def update_default(_):
        return pd.DataFrame(columns=["A"], data=[1])

    @app.callback(Output("log", "children"), Input("store", "children"))
    def update_log(data):
        return data.to_json()

    # Check that stuff works. It doesn't using a normal Dash object.
    dash_duo.start_server(app)
    assert dash_duo.find_element("#store").text == ""
    assert dash_duo.find_element("#log").text == ""
    dash_duo.find_element("#btn").click()
    time.sleep(0.01)  # wait for callback code to execute.
    assert dash_duo.find_element("#store").text != ""
    assert dash_duo.find_element("#log").text == '{"A":{"0":1}}'


def test_serverside_output_transform_memoize(dash_duo):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[ServersideOutputTransform()])
    app.layout = html.Div([
        html.Button(id="btn"),
        html.Div(id="store1"),
        html.Div(id="store2"),
        html.Div(id="log1", children="0"),
        html.Div(id="log2", children="0"),
    ])

    @app.callback(ServersideOutput("store1", "children"), Input("btn", "n_clicks"), memoize=True)
    def update_store1(n_clicks):
        return n_clicks

    @app.callback(Output("log1", "children"), Input("store1", "children"))
    def update_log1(n_clicks):
        return n_clicks

    @app.callback(ServersideOutput("store2", "children", arg_check=False, session_check=False),
                  Input("btn", "n_clicks"), memoize=True)
    def update_store2(n_clicks):
        return n_clicks

    @app.callback(Output("log2", "children"), Input("store2", "children"))
    def update_log2(n_clicks):
        return n_clicks

    # Check that stuff works. It doesn't using a normal Dash object.
    dash_duo.start_server(app)
    dash_duo.find_element("#btn").click()
    time.sleep(1)
    dash_duo.find_element("#btn").click()
    # Args (i.e. n_clicks) included in memoize key, i.e. a call is made on every click.
    dash_duo.wait_for_text_to_equal("#log1", "2", timeout=1)
    # Args (i.e. n_clicks) not included in memoize key, i.e. only one call is made.
    assert dash_duo.find_element("#log2").text == "1"


def test_log_transform(dash_duo):
    app = _get_basic_dash_proxy(transforms=[LogTransform(try_use_mantine=False)])

    @app.callback(Output("log_server", "children"), Input("btn", "n_clicks"), log=True)
    def update_log(n_clicks, dash_logger: DashLogger):
        dash_logger.info("info")
        dash_logger.warning("warning")
        dash_logger.error("error")
        return n_clicks

    # Check that stuff works.
    _basic_dash_proxy_test(dash_duo, app, ["log_server"])
    # Check that log is written to div element.
    assert dash_duo.find_element("#log").text == "INFO: info\nWARNING: warning\nERROR: error"
