from copy import copy
import decimal
import json
import os
import time

import dash
import pandas as pd
import pytest
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Output, Input, State, CallbackBlueprint, html, DashProxy, NoOutputTransform, Trigger, \
    TriggerTransform, MultiplexerTransform, PrefixIdTransform, callback, clientside_callback, DashLogger, LogTransform, \
    BlockingCallbackTransform, dcc, ServersideOutputTransform, ServersideOutput, ALL, CycleBreakerTransform, \
    CycleBreakerInput, DependencyCollection, OperatorTransform, OperatorOutput, Operator, DashBlueprint


# region Test utils/stubs

def _get_basic_dash_proxy(**kwargs) -> DashProxy:
    app = DashProxy(**kwargs)
    app.layout = html.Div([
        html.Button(id="btn"),
        html.Div(id="log_server"),
        html.Div(id="log_client")
    ])
    return app


def _bind_basic_callback(app, flex=False):
    if flex:
        return _bind_basic_callback_flex(app)

    @app.callback(Output("log_server", "children"), Input("btn", "n_clicks"))
    def update_log(n_clicks):
        return n_clicks


def _bind_basic_callback_flex(app):
    @app.callback(output=dict(n=Output("log_server", "children")), inputs=dict(n_clicks=Input("btn", "n_clicks")))
    def update_log(n_clicks):
        return dict(n=n_clicks)


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

@pytest.mark.parametrize(
    'tst, flt',
    [(dict(a=Input("a", "prop"), b=[Input("b", "prop")], c=dict(ca=[Input("ca1", "prop"), Input("ca2", "prop")])),
      [Input("a", "prop"), Input("b", "prop"), Input("ca1", "prop"), Input("ca2", "prop")]),
     ([Input("a", "prop"), Input("b", "prop"), Input("c", "prop")],
      [Input("a", "prop"), Input("b", "prop"), Input("c", "prop")]),
     ((Input("a", "prop"), Input("b", "prop"), Input("c", "prop")),
      [Input("a", "prop"), Input("b", "prop"), Input("c", "prop")])
     ])
def test_dependency_collection(tst, flt):
    dc = DependencyCollection(tst)
    # Test iteration.
    for i, d in enumerate(dc):
        assert d == flt[i]
    # Test access.
    for i in range(len(dc)):
        assert dc[i] == flt[i]
    # Test modification.
    dc[0] = Input("b", "prop")
    assert dc[0] == Input("b", "prop")
    # Test addition.
    _ = dc.append(Input("new", "prop"))
    assert dc[-1] == Input("new", "prop")


def test_callback_blueprint():
    # Test single element.
    cbp = CallbackBlueprint(State("s", "prop"), Output("o", "prop"), Input("i", "prop"))
    assert list(cbp.outputs) == [Output("o", "prop")]
    assert list(cbp.inputs) == [State("s", "prop"), Input("i", "prop")]
    # Test list element.
    cbp = CallbackBlueprint(
        [State("s", "prop"), State("s2", "prop")],
        [Output("o", "prop")],
        [Input("i", "prop")]
    )
    assert list(cbp.outputs) == [Output("o", "prop")]
    assert list(cbp.inputs) == [State("s", "prop"), State("s2", "prop"), Input("i", "prop")]
    # Test mix.
    cbp = CallbackBlueprint(
        [State("s", "prop"), State("s2", "prop")],
        Input("i0", "prop"),
        [Output("o", "prop")],
        State("s3", "prop"),
        [Input("i", "prop")],
        Output("o2", "prop")
    )
    assert list(cbp.outputs) == [Output("o", "prop"), Output("o2", "prop")]
    assert list(cbp.inputs) == [State("s", "prop"), State("s2", "prop"), Input("i0", "prop"),
                                State("s3", "prop"), Input("i", "prop")]
    # Test variables.
    my_input = html.Button()
    my_output = html.Div()
    cbp = CallbackBlueprint(
        Input(my_input, "n_clicks"),
        Output(my_output, "children")
    )
    assert list(cbp.outputs) == [Output(my_output, "children")]
    assert list(cbp.inputs) == [Input(my_input, "n_clicks")]
    # Test kwargs.
    cbp = CallbackBlueprint(
        Input(my_input, "n_clicks"),
        Output(my_output, "children"),
        hello="world"
    )
    assert cbp.kwargs == dict(hello="world")


def test_blueprint_reset():
    bp = DashBlueprint(transforms=[MultiplexerTransform()])
    bp.layout = html.Div([
        html.Button("Left", id="left"),
        html.Button("Right", id="right"),
        html.Div(id="log")
    ])

    @bp.callback(Output("log", "children"), Input("left", "n_clicks"))
    def left(n_clicks):
        if not n_clicks:
            raise PreventUpdate()
        return "left"

    @bp.callback(Output("log", "children"), Input("right", "n_clicks"))
    def right(n_clicks):
        if not n_clicks:
            raise PreventUpdate()
        return "right"

    # Layout without any transforms applied.
    original_layout = copy(bp.layout)
    original_layout_value = copy(bp._layout_value())
    bp.reset()
    assert len(original_layout) == len(original_layout_value)
    # Layout without transforms applied.
    modified_layout = bp.embed(DashProxy())
    assert len(bp.layout.children) == len(original_layout.children)  # should be unmodified
    assert len(modified_layout.children) > len(original_layout.children)
    assert len(bp._layout_value().children) == len(original_layout.children)  # should be unmodified


def test_flexible_callback_signature():
    # Test input/output/state as kwargs.
    cbp = CallbackBlueprint(
        output=[Output("o", "prop")],
        inputs=[Input("i", "prop")],
        hello="world"
    )
    assert list(cbp.inputs) == [Input("i", "prop")]
    assert list(cbp.outputs) == [Output("o", "prop")]
    assert cbp.kwargs == dict(hello="world")
    # Test dict grouping.
    cbp = CallbackBlueprint(
        output=dict(o=Output("o", "prop"), u=Output("u", "prop")),
        inputs=dict(i=Input("i", "prop"), s=State("s", "prop")),
        hello="world"
    )
    assert list(cbp.inputs) == [Input("i", "prop"), State("s", "prop")]
    assert list(cbp.outputs) == [Output("o", "prop"), Output("u", "prop")]
    assert cbp.kwargs == dict(hello="world")
    # Test complex dict grouping.
    cbp = CallbackBlueprint(
        output=[Output("o", "prop"), Output("u", "prop")],
        inputs=dict(w=dict(i=Input("i", "prop"), s=State("s", "prop")), z=dict(i=Input("i2", "prop"))),
        hello="world"
    )
    assert list(cbp.inputs) == [Input("i", "prop"), State("s", "prop"), Input("i2", "prop")]
    assert list(cbp.outputs) == [Output("o", "prop"), Output("u", "prop")]
    assert cbp.kwargs == dict(hello="world")


def test_flexible_callback_signature_in_app(dash_duo):
    app = DashProxy()
    app.layout = html.Div([
        html.Div(id="a", children="a"),
        html.Div(id="b", children="b"),
        html.Div(id="log", children=None),
    ])

    @app.callback(output=dict(x=Output("log", "children")),
                  inputs=dict(dict(g=dict(a=Input("a", "children"), b=Input("b", "children")))))
    def update_x(g):
        return dict(x=f"{g['a']}_{g['b']}")

    dash_duo.start_server(app)
    time.sleep(0.1)
    x = dash_duo.find_element("#log")
    assert x.text == "a_b"


def test_dash_proxy(dash_duo):
    app = _get_basic_dash_proxy()
    _bind_basic_callback(app)
    _bind_basic_clientside_callback(app)
    # Check that both server and client side callbacks work.
    _basic_dash_proxy_test(dash_duo, app)


def test_dash_output_input_state_compatibility(dash_duo):
    app = _get_basic_dash_proxy()

    @app.callback(dash.Output("log_server", "children"),
                  dash.Input("btn", "n_clicks"),
                  dash.State("btn", "n_clicks"))
    def update_log(n_clicks, state):
        return n_clicks

    _basic_dash_proxy_test(dash_duo, app, element_ids=["log_server"])


@pytest.mark.parametrize(
    'args, kwargs',
    [([Input("btn", "n_clicks")], dict()),
     ([], dict(inputs=dict(n_clicks=Input("btn", "n_clicks"))))])
def test_no_output_transform(dash_duo, args, kwargs):
    app = DashProxy()
    app.layout = html.Div([
        html.Button(id="btn"),
    ])

    @app.callback(*args, **kwargs)
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


@pytest.mark.parametrize(
    'args, kwargs',
    [([Output("log", "children"), Input("right", "n_clicks")], dict()),
     ([], dict(output=[Output("log", "children")], inputs=dict(n_clicks=Input("right", "n_clicks"))))])
def test_multiplexer_transform(dash_duo, args, kwargs):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[MultiplexerTransform()])
    app.layout = html.Div([
        html.Button(id="left"),
        html.Button(id="right"),
        html.Div(id="log"),
    ])
    app.clientside_callback("function(x){return 'left'}", Output("log", "children"), Input("left", "n_clicks"))

    @app.callback(*args, **kwargs)
    def update_right(n_clicks):
        return ["right"]

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


@pytest.mark.parametrize('flex', [False, True])
def test_prefix_id_transform(dash_duo, flex):
    app = _get_basic_dash_proxy(transforms=[PrefixIdTransform(prefix="x")])
    _bind_basic_callback(app, flex)
    _bind_basic_clientside_callback(app)
    # Check that both server and client side callbacks work.
    _basic_dash_proxy_test(dash_duo, app, ["x-log_server", "x-log_client"], "x-btn")


@pytest.mark.parametrize(
    'args, kwargs',
    [([Output("log", "children"), Input("right", "n_clicks")], dict()),
     ([], dict(output=[Output("log", "children")], inputs=dict(n_clicks=Input("right", "n_clicks"))))])
def test_multiplexer_and_prefix_transform(dash_duo, args, kwargs):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[PrefixIdTransform("prefix"), MultiplexerTransform()])
    app.layout = html.Div([
        html.Button(id="left"),
        html.Button(id="right"),
        html.Div(id="log"),
    ])
    app.clientside_callback("function(x){return 'left'}", Output("log", "children"), Input("left", "n_clicks"))

    @app.callback(*args, **kwargs)
    def update_right(n_clicks):
        return ["right"]

    # Check that the app works.
    dash_duo.start_server(app)
    log = dash_duo.find_element("#prefix-log")
    assert log.text == ""
    dash_duo.find_element("#prefix-left").click()
    dash_duo.wait_for_text_to_equal("#prefix-log", "left", timeout=0.1)
    assert log.text == "left"
    dash_duo.find_element("#prefix-right").click()
    dash_duo.wait_for_text_to_equal("#prefix-log", "right", timeout=0.1)
    assert log.text == "right"


def test_global_blueprint(dash_duo):
    app = _get_basic_dash_proxy()
    clientside_callback("function(x){return x;}",
                        Output("log_client", "children"), Input("btn", "n_clicks"))

    @callback(Output("log_server", "children"), Input("btn", "n_clicks"))
    def update_log(n_clicks):
        return n_clicks

    # Check that callbacks work.
    _basic_dash_proxy_test(dash_duo, app)


@pytest.mark.parametrize(
    'args, kwargs, port',
    [([Output("log", "children"), Input("trigger", "n_intervals")], dict(), 4757),
     ([], dict(output=[Output("log", "children")],
               inputs=dict(tick=Input("trigger", "n_intervals"))), 4758)])
def test_blocking_callback_transform(dash_duo, args, kwargs, port):
    app = DashProxy(transforms=[BlockingCallbackTransform(timeout=5)])
    app.layout = html.Div([html.Div(id="log"), dcc.Interval(id="trigger", interval=500)])
    msg = "Hello world!"

    @app.callback(*args, **kwargs, blocking=True)
    def update(tick):
        time.sleep(1)
        return [msg]

    # Check that stuff works. It doesn't using a normal Dash object.
    dash_duo.start_server(app, port=port)
    dash_duo.wait_for_text_to_equal("#log", msg, timeout=5)
    assert dash_duo.find_element("#log").text == msg


def test_blocking_callback_transform_final_invocation(dash_duo):
    app = DashProxy(transforms=[BlockingCallbackTransform(timeout=5)])
    app.layout = html.Div([html.Div(id="log"), dcc.Input(id="input")])

    @app.callback(Output("log", "children"), Input("input", "value"), blocking=True)
    def update(value):
        time.sleep(0.2)
        return value

    dash_duo.start_server(app)
    f = dash_duo.find_element("#input")
    f.send_keys("a")
    f.send_keys("b")
    f.send_keys("c")
    dash_duo.wait_for_text_to_equal("#log", "abc", timeout=5)  # final invocation


@pytest.mark.parametrize(
    'args, kwargs',
    [([ServersideOutput("store", "children"), Input("btn", "n_clicks")], dict()),
     ([], dict(output=ServersideOutput("store", "children"),
               inputs=dict(n_clicks=Input("btn", "n_clicks"))))])
def test_serverside_output_transform(dash_duo, args, kwargs):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[ServersideOutputTransform()])
    app.layout = html.Div([
        html.Button(id="btn"),
        html.Div(id="store"),
        html.Div(id="log"),
    ])

    @app.callback(*args, **kwargs)
    def update_default(n_clicks):
        return pd.DataFrame(columns=["A"], data=[1])

    @app.callback(Output("log", "children"), Input("store", "children"))
    def update_log(data):
        return data.to_json()

    # Check that stuff works. It doesn't using a normal Dash object.
    dash_duo.start_server(app)
    assert dash_duo.find_element("#store").text == ""
    assert dash_duo.find_element("#log").text == ""
    dash_duo.find_element("#btn").click()
    time.sleep(0.1)  # wait for callback code to execute.
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


@pytest.mark.parametrize(
    'args, kwargs',
    [([Output("log_server", "children"), Input("btn", "n_clicks")], dict()),
     ([], dict(output=[Output("log_server", "children")],
               inputs=dict(n_clicks=Input("btn", "n_clicks"))))])
def test_log_transform(dash_duo, args, kwargs):
    app = _get_basic_dash_proxy(transforms=[LogTransform(try_use_mantine=False)])

    @app.callback(*args, **kwargs, log=True)
    def update_log(n_clicks, dash_logger: DashLogger):
        dash_logger.info("info")
        dash_logger.warning("warning")
        dash_logger.error("error")
        return n_clicks

    # Check that stuff works.
    _basic_dash_proxy_test(dash_duo, app, ["log_server"])
    # Check that log is written to div element.
    assert dash_duo.find_element("#log").text == "INFO: info\nWARNING: warning\nERROR: error"


@pytest.mark.parametrize(
    'c_args, c_kwargs, f_args, f_kwargs',
    [([Output("celsius", "value"), CycleBreakerInput("fahrenheit", "value")], dict(),
      [Output("fahrenheit", "value"), Input("celsius", "value")], dict()),
     ([], dict(output=Output("celsius", "value"), inputs=dict(value=CycleBreakerInput("fahrenheit", "value"))),
      [], dict(output=Output("fahrenheit", "value"), inputs=dict(value=Input("celsius", "value"))))
     ])
def test_cycle_breaker_transform(dash_duo, c_args, c_kwargs, f_args, f_kwargs):
    app = DashProxy(transforms=[CycleBreakerTransform()])
    app.layout = html.Div([
        dcc.Input(id="celsius", type="number"),
        dcc.Input(id="fahrenheit", type="number"),
    ])

    def validate_input(value) -> decimal:
        if value is None:
            raise PreventUpdate()
        try:
            return decimal.Decimal(value)
        except ValueError:
            raise PreventUpdate()

    @app.callback(*c_args, **c_kwargs)
    def update_celsius(value):
        return str((validate_input(value) - 32) / 9 * 5)

    @app.callback(*f_args, **f_kwargs)
    def update_fahrenheit(value):
        return str(validate_input(value) / 5 * 9 + 32)

    dash_duo.start_server(app)
    time.sleep(0.1)
    logs = dash_duo.get_logs()
    assert len(logs) <= int(os.environ.get("TEST_CYCLE_BREAKER_ALLOWED_ERRORS", "0"))
    f = dash_duo.find_element("#fahrenheit")
    f.send_keys("32")
    dash_duo.wait_for_text_to_equal("#celsius", "0", timeout=1)
    c = dash_duo.find_element("#celsius")
    c.send_keys("100")
    dash_duo.wait_for_text_to_equal("#fahrenheit", "212", timeout=1)


def test_list_output(dash_duo):
    gui_actions = dict(
        append=lambda x: Operator().list.append(x),
        extend=lambda x: Operator().list.extend([x, x]),
        sort=lambda x: Operator().list.sort(),
        reverse=lambda x: Operator().list.reverse(),
        clear=lambda x: Operator().list.reset(),
        insert=lambda x: Operator().list.insert(4, "hest"),
        remove=lambda x: Operator().list.remove(3),
        pop=lambda x: Operator().list.pop(3),
    )
    action_buttons = [html.Button(k, id=k) for k in gui_actions]
    app = DashProxy(transforms=[OperatorTransform()], prevent_initial_callbacks=True)
    app.layout = html.Div(action_buttons + [dcc.Store(id="store"), html.Div(id="log")])
    for k in gui_actions:
        app.callback(OperatorOutput("store", "data"), Input(k, "n_clicks"))(gui_actions[k])
    app.callback(Output("log", "children"), Input("store", "data"))(lambda data: json.dumps(data))
    # Start stuff.
    proxy_list = []
    dash_duo.start_server(app)
    # Check empty after clear.
    dash_duo.find_element("#clear").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    # Check append.
    proxy_list.append(1)
    dash_duo.find_element("#append").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    proxy_list.append(2)
    dash_duo.find_element("#append").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    proxy_list.append(3)
    dash_duo.find_element("#append").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    proxy_list.append(4)
    dash_duo.find_element("#append").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    # Check extend.
    proxy_list.extend([1, 1])
    dash_duo.find_element("#extend").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    proxy_list.extend([2, 2])
    dash_duo.find_element("#extend").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    # Check sort.
    proxy_list.sort()
    dash_duo.find_element("#sort").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    # Check reverse.
    proxy_list.reverse()
    dash_duo.find_element("#reverse").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    # Check remove.
    proxy_list.remove(3)
    dash_duo.find_element("#remove").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    # Check pop.
    proxy_list.pop(3)
    dash_duo.find_element("#pop").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    # Check insert.
    proxy_list.insert(4, "hest")
    dash_duo.find_element("#insert").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)
    # Check empty after clear.
    proxy_list.clear()
    dash_duo.find_element("#clear").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_list), timeout=1)


def test_dict_output(dash_duo):
    pop_key = "some_key2"
    update_dict = dict(key="value", some="stuff", foo="bar")
    gui_actions = dict(
        set=lambda x: Operator().dict.set(f"some_key{x}", f"some_value{x}"),
        clear=lambda x: Operator().dict.reset(),
        pop=lambda x: Operator().dict.pop(pop_key),
        update=lambda x: Operator().dict.update(update_dict),
    )
    action_buttons = [html.Button(k, id=k) for k in gui_actions]
    app = DashProxy(transforms=[OperatorTransform()], prevent_initial_callbacks=True)
    app.layout = html.Div(action_buttons + [dcc.Store(id="store"), html.Div(id="log")])
    for k in gui_actions:
        app.callback(OperatorOutput("store", "data"), Input(k, "n_clicks"))(gui_actions[k])
    app.callback(Output("log", "children"), Input("store", "data"))(lambda data: json.dumps(data))
    # Start stuff.
    proxy_dict = {}
    dash_duo.start_server(app)
    # Check empty after clear.
    dash_duo.find_element("#clear").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_dict), timeout=1)
    # Check set.
    proxy_dict["some_key1"] = "some_value1"
    dash_duo.find_element("#set").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_dict), timeout=1)
    proxy_dict["some_key2"] = "some_value2"
    dash_duo.find_element("#set").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_dict), timeout=1)
    proxy_dict["some_key3"] = "some_value3"
    dash_duo.find_element("#set").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_dict), timeout=1)
    # Check pop.
    proxy_dict.pop(pop_key)
    dash_duo.find_element("#pop").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_dict), timeout=1)
    # Check update.
    proxy_dict.update(update_dict)
    dash_duo.find_element("#update").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(proxy_dict), timeout=1)


def test_index_accessor(dash_duo):
    some_value = "some_value"
    gui_actions = [
        dict(id="list_idx", opr=lambda x: Operator()[1].assign(some_value), data=["bar", "bar", "bar"]),
        dict(id="dict_key", opr=lambda x: Operator()['foo'].assign(some_value), data={"foo": "bar", "foo2": "bar2"}),
        dict(id="composite", opr=lambda x: Operator()[1]['foo'][0].assign(some_value),
             data=[
                 "bar",
                 {"foo": ["bar", "bar", "bar"], "foo2": "bar2"},
                 "bar"
             ]),
    ]
    action_buttons = [html.Button(e['id'], id=e['id']) for e in gui_actions]
    stores = [dcc.Store(data=e['data'], id=f"store_{e['id']}") for e in gui_actions]
    app = DashProxy(transforms=[OperatorTransform(), MultiplexerTransform()], prevent_initial_callbacks=True)
    app.layout = html.Div(action_buttons + stores + [html.Div(id="log")])
    for e in gui_actions:
        app.callback(OperatorOutput(f"store_{e['id']}", "data"), Input(e['id'], "n_clicks"))(e['opr'])
        app.callback(Output("log", "children"), Input(f"store_{e['id']}", "data"))(lambda x: json.dumps(x))
    # Start stuff.
    dash_duo.start_server(app)
    # Check list_index.
    data = gui_actions[0]['data']
    data[1] = some_value
    dash_duo.find_element("#list_idx").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(data), timeout=1)
    # Check dict_key.
    data = gui_actions[1]['data']
    data['foo'] = some_value
    dash_duo.find_element("#dict_key").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(data), timeout=1)
    # Check composite.
    data = gui_actions[2]['data']
    data[1]['foo'][0] = some_value
    dash_duo.find_element("#composite").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(data), timeout=1)


def test_composite_operator(dash_duo):
    data = [1, 2, 3, 4, 5]
    app = DashProxy(transforms=[OperatorTransform()], prevent_initial_callbacks=True)
    app.layout = html.Div([html.Button(id="action"), dcc.Store(id="store", data=data), html.Div(id="log")])
    app.callback(Output("log", "children"), Input("store", "data"))(lambda x: json.dumps(x))

    @app.callback(OperatorOutput("store", "data"), Input("action", "n_clicks"))
    def action(_):
        o = Operator()
        o[2] = 7
        o[4] = -1
        o.list.sort()
        return o

    # Start stuff.
    dash_duo.start_server(app)
    # Test stuff.
    data[2] = 7
    data[4] = -1
    data = sorted(data)
    dash_duo.find_element("#action").click()
    dash_duo.wait_for_text_to_equal("#log", json.dumps(data), timeout=1)
