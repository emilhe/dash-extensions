from enrich import DashBlueprint, Output, Input, State


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


