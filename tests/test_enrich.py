import decimal
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime

import dash
import pandas as pd
import pytest
from dash.exceptions import PreventUpdate
from pydantic import BaseModel

import dash_extensions.enrich
from dash_extensions.enrich import (
    ALL,
    MATCH,
    BaseModelTransform,
    BlockingCallbackTransform,
    CallbackBlueprint,
    CycleBreakerInput,
    CycleBreakerTransform,
    DashBlueprint,
    DashLogger,
    DashProxy,
    DataclassTransform,
    DependencyCollection,
    Input,
    LogTransform,
    MultiplexerTransform,
    NoOutputTransform,
    Output,
    PrefixIdTransform,
    Serverside,
    ServersideOutputTransform,
    State,
    Trigger,
    TriggerTransform,
    callback,
    clientside_callback,
    dcc,
    html,
)

# region Test utils/stubs


def _stringify_id(id_):
    if isinstance(id_, dict):
        return json.dumps(id_, sort_keys=True, separators=(",", ":"))
    return id_


def _css_escape(s):
    sel = re.sub("[\\{\\}\\\"\\'.:,]", lambda m: "\\" + m.group(0), s)
    return sel


def _css_selector(_id):
    return f"#{_css_escape(_stringify_id(_id))}"


def _cssid(**kwargs):
    # escaped CSS for object IDs
    kvs = r"\,".join([r"\"" + k + r"\"\:\"" + kwargs[k] + r"\"" for k in kwargs])
    return r"#\{" + kvs + r"\}"


def _get_basic_dash_proxy(**kwargs) -> DashProxy:
    app = DashProxy(**kwargs)
    app.layout = html.Div([html.Button(id="btn"), html.Div(id="log_server"), html.Div(id="log_client")])
    return app


def _bind_basic_callback(app, flex=False):
    if flex:
        return _bind_basic_callback_flex(app)

    @app.callback(Output("log_server", "children"), Input("btn", "n_clicks"))
    def update_log(n_clicks):
        return n_clicks


def _bind_basic_callback_flex(app):
    @app.callback(
        output=dict(n=Output("log_server", "children")),
        inputs=dict(n_clicks=Input("btn", "n_clicks")),
    )
    def update_log(n_clicks):
        return dict(n=n_clicks)


def _bind_basic_clientside_callback(app):
    app.clientside_callback(
        "function(x){return x;}",
        Output("log_client", "children"),
        Input("btn", "n_clicks"),
    )


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
    "tst, flt",
    [
        (
            dict(
                a=Input("a", "prop"),
                b=[Input("b", "prop")],
                c=dict(ca=[Input("ca1", "prop"), Input("ca2", "prop")]),
            ),
            [
                Input("a", "prop"),
                Input("b", "prop"),
                Input("ca1", "prop"),
                Input("ca2", "prop"),
            ],
        ),
        (
            [Input("a", "prop"), Input("b", "prop"), Input("c", "prop")],
            [Input("a", "prop"), Input("b", "prop"), Input("c", "prop")],
        ),
        (
            (Input("a", "prop"), Input("b", "prop"), Input("c", "prop")),
            [Input("a", "prop"), Input("b", "prop"), Input("c", "prop")],
        ),
    ],
)
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
        [Input("i", "prop")],
    )
    assert list(cbp.outputs) == [Output("o", "prop")]
    assert list(cbp.inputs) == [
        State("s", "prop"),
        State("s2", "prop"),
        Input("i", "prop"),
    ]
    # Test mix.
    cbp = CallbackBlueprint(
        [State("s", "prop"), State("s2", "prop")],
        Input("i0", "prop"),
        [Output("o", "prop")],
        State("s3", "prop"),
        [Input("i", "prop")],
        Output("o2", "prop"),
    )
    assert list(cbp.outputs) == [Output("o", "prop"), Output("o2", "prop")]
    assert list(cbp.inputs) == [
        State("s", "prop"),
        State("s2", "prop"),
        Input("i0", "prop"),
        State("s3", "prop"),
        Input("i", "prop"),
    ]
    # Test variables.
    my_input = html.Button()
    my_output = html.Div()
    cbp = CallbackBlueprint(Input(my_input, "n_clicks"), Output(my_output, "children"))
    assert list(cbp.outputs) == [Output(my_output, "children")]
    assert list(cbp.inputs) == [Input(my_input, "n_clicks")]
    # Test kwargs.
    cbp = CallbackBlueprint(Input(my_input, "n_clicks"), Output(my_output, "children"), hello="world")
    assert cbp.kwargs == dict(hello="world")


def test_flexible_callback_signature():
    # Test input/output/state as kwargs.
    cbp = CallbackBlueprint(output=[Output("o", "prop")], inputs=[Input("i", "prop")], hello="world")
    assert list(cbp.inputs) == [Input("i", "prop")]
    assert list(cbp.outputs) == [Output("o", "prop")]
    assert cbp.kwargs == dict(hello="world")
    # Test dict grouping.
    cbp = CallbackBlueprint(
        output=dict(o=Output("o", "prop"), u=Output("u", "prop")),
        inputs=dict(i=Input("i", "prop"), s=State("s", "prop")),
        hello="world",
    )
    assert list(cbp.inputs) == [Input("i", "prop"), State("s", "prop")]
    assert list(cbp.outputs) == [Output("o", "prop"), Output("u", "prop")]
    assert cbp.kwargs == dict(hello="world")
    # Test complex dict grouping.
    cbp = CallbackBlueprint(
        output=[Output("o", "prop"), Output("u", "prop")],
        inputs=dict(
            w=dict(i=Input("i", "prop"), s=State("s", "prop")),
            z=dict(i=Input("i2", "prop")),
        ),
        hello="world",
    )
    assert list(cbp.inputs) == [
        Input("i", "prop"),
        State("s", "prop"),
        Input("i2", "prop"),
    ]
    assert list(cbp.outputs) == [Output("o", "prop"), Output("u", "prop")]
    assert cbp.kwargs == dict(hello="world")


def test_flexible_callback_signature_in_app(dash_duo):
    app = DashProxy()
    app.layout = html.Div(
        [
            html.Div(id="a", children="a"),
            html.Div(id="b", children="b"),
            html.Div(id="log", children=None),
        ]
    )

    @app.callback(
        output=dict(x=Output("log", "children")),
        inputs=dict(dict(g=dict(a=Input("a", "children"), b=Input("b", "children")))),
    )
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

    @app.callback(
        dash.Output("log_server", "children"),
        dash.Input("btn", "n_clicks"),
        dash.State("btn", "n_clicks"),
    )
    def update_log(n_clicks, state):
        return n_clicks

    _basic_dash_proxy_test(dash_duo, app, element_ids=["log_server"])


@pytest.mark.parametrize(
    "args, kwargs",
    [
        ([Input("btn", "n_clicks")], dict()),
        ([], dict(inputs=dict(n_clicks=Input("btn", "n_clicks")))),
    ],
)
def test_no_output_transform(dash_duo, args, kwargs):
    app = DashProxy()
    app.layout = html.Div(
        [
            html.Button(id="btn"),
        ]
    )

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
    app.layout = html.Div(
        [
            html.Button(id="btn1"),
            html.Button(id="btn2"),
            html.Button(id="btn3"),
            html.Button(id="btn4"),
            html.Div(id="log"),
        ]
    )

    @app.callback(
        Output("log", "children"),
        Trigger("btn1", "n_clicks"),
        Input("btn2", "n_clicks"),
        Trigger("btn3", "n_clicks"),
        State("btn4", "n_clicks"),
    )
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


def test_trigger_transform_clientside(dash_duo):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[TriggerTransform()])
    app.layout = html.Div(
        [
            html.Button(id="btn1"),
            html.Button(id="btn2"),
            html.Button(id="btn3"),
            html.Button(id="btn4"),
            html.Div(id="log"),
        ]
    )

    app.clientside_callback(
        """(nClicks2, nClicks4) => `${nClicks2}-${nClicks4}`""",
        Output("log", "children"),
        Trigger("btn1", "n_clicks"),
        Input("btn2", "n_clicks"),
        Trigger("btn3", "n_clicks"),
        State("btn4", "n_clicks"),
    )

    # Check that the app works.
    dash_duo.start_server(app)
    log = dash_duo.find_element("#log")
    assert log.text == ""
    dash_duo.find_element("#btn1").click()
    time.sleep(0.1)
    assert log.text == "undefined-undefined"
    dash_duo.find_element("#btn2").click()
    time.sleep(0.1)
    assert log.text == "1-undefined"
    dash_duo.find_element("#btn4").click()
    time.sleep(0.1)
    assert log.text == "1-undefined"
    dash_duo.find_element("#btn3").click()
    time.sleep(0.1)
    assert log.text == "1-1"


@pytest.mark.parametrize(
    "args, kwargs",
    [
        ([Output("log", "children"), Input("right", "n_clicks")], dict()),
        (
            [],
            dict(
                output=[Output("log", "children")],
                inputs=dict(n_clicks=Input("right", "n_clicks")),
            ),
        ),
    ],
)
def test_multiplexer_transform(dash_duo, args, kwargs):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[MultiplexerTransform()])
    app.layout = html.Div(
        [
            html.Button(id="left"),
            html.Button(id="right"),
            html.Div(id="log"),
        ]
    )
    app.clientside_callback(
        "function(x){return 'left'}",
        Output("log", "children"),
        Input("left", "n_clicks"),
    )

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
        @app.callback(
            Output({"type": "div", "id": ALL}, "children"),
            Input({"type": f"button{i}", "id": ALL}, "n_clicks"),
        )
        def func(n):
            return [f"Hello from group {i}"] * len(n)

    def make_block(i):
        layout = [
            html.Button(f"Button 0 in group {i}", id={"type": f"button{i}", "id": "x"}),
            html.Button(f"Button 1 in group {i}", id={"type": f"button{i}", "id": "y"}),
            html.Div(f"Div {i}", id={"type": "div", "id": i}),
        ]
        make_callback(i)
        return layout

    app = DashProxy(transforms=[MultiplexerTransform()], prevent_initial_callbacks=True)
    app.layout = html.Div(make_block("0") + make_block("1"))

    dash_duo.start_server(app)
    dash_duo.find_element(_cssid(id="x", type="button0")).click()
    assert dash_duo.find_element(_cssid(id="0", type="div")).text == "Hello from group 0"
    dash_duo.find_element(_cssid(id="y", type="button1")).click()
    assert dash_duo.find_element(_cssid(id="1", type="div")).text == "Hello from group 1"


@pytest.mark.parametrize("flex", [False, True])
def test_prefix_id_transform(dash_duo, flex):
    app = _get_basic_dash_proxy(transforms=[PrefixIdTransform(prefix="x")])
    _bind_basic_callback(app, flex)
    _bind_basic_clientside_callback(app)
    # Check that both server and client side callbacks work.
    _basic_dash_proxy_test(dash_duo, app, ["x-log_server", "x-log_client"], "x-btn")


@pytest.mark.parametrize(
    "args, kwargs",
    [
        ([Output("log", "children"), Input("right", "n_clicks")], dict()),
        (
            [],
            dict(
                output=[Output("log", "children")],
                inputs=dict(n_clicks=Input("right", "n_clicks")),
            ),
        ),
    ],
)
def test_multiplexer_and_prefix_transform(dash_duo, args, kwargs):
    app = DashProxy(
        prevent_initial_callbacks=True,
        transforms=[PrefixIdTransform("prefix"), MultiplexerTransform()],
    )
    app.layout = html.Div(
        [
            html.Button(id="left"),
            html.Button(id="right"),
            html.Div(id="log"),
        ]
    )
    app.clientside_callback(
        "function(x){return 'left'}",
        Output("log", "children"),
        Input("left", "n_clicks"),
    )

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
    clientside_callback(
        "function(x){return x;}",
        Output("log_client", "children"),
        Input("btn", "n_clicks"),
    )

    @callback(Output("log_server", "children"), Input("btn", "n_clicks"))
    def update_log(n_clicks):
        return n_clicks

    # Check that callbacks work.
    _basic_dash_proxy_test(dash_duo, app)
    # Reset changes.
    dash_extensions.enrich.GLOBAL_BLUEPRINT = DashBlueprint()


@pytest.mark.parametrize(
    "args, kwargs, port",
    [
        ([Output("log", "children"), Input("trigger", "n_intervals")], dict(), 4757),
        (
            [],
            dict(
                output=[Output("log", "children")],
                inputs=dict(tick=Input("trigger", "n_intervals")),
            ),
            4758,
        ),
    ],
)
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
    "args, kwargs",
    [
        ([Output("store", "children"), Input("btn", "n_clicks")], dict()),
        (
            [],
            dict(
                output=Output("store", "children"),
                inputs=dict(n_clicks=Input("btn", "n_clicks")),
            ),
        ),
    ],
)
def test_dataclass_transform(dash_duo, args, kwargs):
    @dataclass
    class StateModel:
        value: datetime
        list_of_values: list[int]

    app = DashProxy(prevent_initial_callbacks=True, transforms=[DataclassTransform()])
    app.layout = html.Div(
        [
            html.Button(id="btn"),
            dcc.Store(id="store"),
            html.Div(id="log"),
        ]
    )

    @app.callback(Output("store", "data"), Input("btn", "n_clicks"))
    def update_default(n_clicks: str):
        return StateModel(value=datetime(2000, 1, 1), list_of_values=[1, 2, 3, 4, 5])

    @app.callback(Output("log", "children"), Input("store", "data"))
    def update_log(state: StateModel):
        return f"{state.value.isoformat()}: {str(state.list_of_values)}"

    # Check that stuff works. It doesn't using a normal Dash object.
    dash_duo.start_server(app)
    assert dash_duo.find_element("#log").text == ""
    dash_duo.find_element("#btn").click()
    time.sleep(0.1)  # wait for callback code to execute.
    assert dash_duo.find_element("#log").text == "2000-01-01T00:00:00: [1, 2, 3, 4, 5]"


@pytest.mark.parametrize(
    "args, kwargs",
    [
        ([Output("store", "children"), Input("btn", "n_clicks")], dict()),
        (
            [],
            dict(
                output=Output("store", "children"),
                inputs=dict(n_clicks=Input("btn", "n_clicks")),
            ),
        ),
    ],
)
def test_base_model_transform(dash_duo, args, kwargs):
    class StateModel(BaseModel):
        value: datetime
        list_of_values: list[int]

    app = DashProxy(prevent_initial_callbacks=True, transforms=[BaseModelTransform()])
    app.layout = html.Div(
        [
            html.Button(id="btn"),
            dcc.Store(id="store"),
            html.Div(id="log"),
        ]
    )

    @app.callback(Output("store", "data"), Input("btn", "n_clicks"))
    def update_default(n_clicks: str):
        return StateModel(value=datetime(2000, 1, 1), list_of_values=[1, 2, 3, 4, 5])

    @app.callback(Output("log", "children"), Input("store", "data"))
    def update_log(state: StateModel):
        return f"{state.value.isoformat()}: {str(state.list_of_values)}"

    # Check that stuff works. It doesn't using a normal Dash object.
    dash_duo.start_server(app)
    assert dash_duo.find_element("#log").text == ""
    dash_duo.find_element("#btn").click()
    time.sleep(0.1)  # wait for callback code to execute.
    assert dash_duo.find_element("#log").text == "2000-01-01T00:00:00: [1, 2, 3, 4, 5]"


@pytest.mark.parametrize(
    "args, kwargs",
    [
        ([Output("store", "children"), Input("btn", "n_clicks")], dict()),
        (
            [],
            dict(
                output=Output("store", "children"),
                inputs=dict(n_clicks=Input("btn", "n_clicks")),
            ),
        ),
    ],
)
def test_serverside_output_transform(dash_duo, args, kwargs):
    app = DashProxy(prevent_initial_callbacks=True, transforms=[ServersideOutputTransform()])
    app.layout = html.Div(
        [
            html.Button(id="btn"),
            html.Div(id="store"),
            html.Div(id="log"),
        ]
    )

    @app.callback(*args, **kwargs)
    def update_default(n_clicks):
        return Serverside(pd.DataFrame(columns=["A"], data=[1]))

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


def test_serverside_output_transform_wildcard(dash_duo):  # noqa: C901
    def _id(t, i):
        return {"type": t, "index": i}

    def make_block(i):
        return [
            html.Button(id=_id("btn", i)),
            html.Div(id=_id("sso", i)),
            html.Div(id=_id("log", i)),
        ]

    app = DashProxy(
        prevent_initial_callbacks=True,
        transforms=[ServersideOutputTransform(), MultiplexerTransform()],
    )
    app.layout = html.Div(make_block("1") + make_block("2") + [html.Div(id="log_all"), html.Button(id="btn_all")])

    @app.callback(Output(_id("sso", MATCH), "children"), Input(_id("btn", MATCH), "n_clicks"))
    def update_default(n_clicks):
        """
        Populate serverside output ONE at a time, i.e. WRITE to SSO using MATCH.
        """
        return Serverside(pd.DataFrame(columns=["A"], data=[n_clicks]))

    @app.callback(Output(_id("sso", ALL), "children"), Input("btn_all", "n_clicks"))
    def update_all(n_clicks):
        """
        Populate serverside output ALL at once, i.e. WRITE to SSO using ALL.
        """
        return tuple([Serverside(pd.DataFrame(columns=["B"], data=[n_clicks]))] * 2)

    @app.callback(Output(_id("log", MATCH), "children"), Input(_id("sso", MATCH), "children"))
    def update_log(data):
        """
        Populate log elements ONE at a time, i.e. READ from SSO using MATCH.
        """
        return data.to_json()

    @app.callback(Output("log_all", "children"), Input(_id("sso", ALL), "children"))
    def update_log_all(data):
        """
        Populate ALL log elements, i.e. READ from SSO using ALL.
        """
        return [d.to_json() if d is not None else "None" for d in data]

    dash_duo.start_server(app)
    assert dash_duo.find_element(_css_selector(_id("sso", "1"))).text == ""
    assert dash_duo.find_element(_css_selector(_id("log", "1"))).text == ""
    assert dash_duo.find_element(_css_selector(_id("sso", "2"))).text == ""
    assert dash_duo.find_element(_css_selector(_id("log", "2"))).text == ""
    # Click the first element.
    dash_duo.find_element(_css_selector(_id("btn", "1"))).click()
    time.sleep(0.1)  # wait for callback code to execute.
    assert dash_duo.find_element(_css_selector(_id("sso", "2"))).text == ""  # not clicked, should be blank
    assert dash_duo.find_element(_css_selector(_id("log", "2"))).text == ""  # not clicked, should be blank
    assert dash_duo.find_element(_css_selector(_id("sso", "1"))).text != ""
    assert dash_duo.find_element(_css_selector(_id("log", "1"))).text == '{"A":{"0":1}}'
    assert dash_duo.find_element(_css_selector("log_all")).text == '{"A":{"0":1}}None'
    # Click the second element twice.
    dash_duo.find_element(_css_selector(_id("btn", "2"))).click()
    time.sleep(0.1)  # wait for callback code to execute.
    dash_duo.find_element(_css_selector(_id("btn", "2"))).click()
    time.sleep(0.1)  # wait for callback code to execute.
    assert dash_duo.find_element(_css_selector(_id("sso", "2"))).text != ""  # not clicked, should be blank
    assert dash_duo.find_element(_css_selector(_id("log", "2"))).text == '{"A":{"0":2}}'  # not clicked, should be blank
    assert dash_duo.find_element(_css_selector(_id("log", "1"))).text == '{"A":{"0":1}}'
    assert dash_duo.find_element(_css_selector("log_all")).text == '{"A":{"0":1}}{"A":{"0":2}}'
    # Click the all element.
    dash_duo.find_element("#btn_all").click()
    time.sleep(0.1)  # wait for callback code to execute.
    assert dash_duo.find_element(_css_selector("log_all")).text == '{"B":{"0":1}}{"B":{"0":1}}'


@pytest.mark.parametrize(
    "args, kwargs",
    [
        ([Output("log_server", "children"), Input("btn", "n_clicks")], dict()),
        (
            [],
            dict(
                output=[Output("log_server", "children")],
                inputs=dict(n_clicks=Input("btn", "n_clicks")),
            ),
        ),
    ],
)
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
    "c_args, c_kwargs, f_args, f_kwargs",
    [
        (
            [Output("celsius", "value"), CycleBreakerInput("fahrenheit", "value")],
            dict(),
            [Output("fahrenheit", "value"), Input("celsius", "value")],
            dict(),
        ),
        (
            [],
            dict(
                output=Output("celsius", "value"),
                inputs=dict(value=CycleBreakerInput("fahrenheit", "value")),
            ),
            [],
            dict(
                output=Output("fahrenheit", "value"),
                inputs=dict(value=Input("celsius", "value")),
            ),
        ),
    ],
)
def test_cycle_breaker_transform(dash_duo, c_args, c_kwargs, f_args, f_kwargs):  # noqa: C901
    app = DashProxy(transforms=[CycleBreakerTransform()])
    app.layout = html.Div(
        [
            dcc.Input(id="celsius", type="number"),
            dcc.Input(id="fahrenheit", type="number"),
        ]
    )

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
    logs = [entry for entry in dash_duo.driver.get_log("browser") if entry["timestamp"] > dash_duo._last_ts]
    assert len(logs) <= int(os.environ.get("TEST_CYCLE_BREAKER_ALLOWED_ERRORS", "0"))
    f = dash_duo.find_element("#fahrenheit")
    f.send_keys("32")
    dash_duo.wait_for_text_to_equal("#celsius", "0", timeout=1)
    c = dash_duo.find_element("#celsius")
    c.send_keys("100")
    dash_duo.wait_for_text_to_equal("#fahrenheit", "212", timeout=1)
