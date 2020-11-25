"""Useless app showing intrinsically complex setup with ids as string and dicts and callback
dependencies on them using or not matching with ALL and MATCH.

Objective is for Dash to not complain ;-). The app does nothing per se.

"""
import logging
import sys

import dash_html_components as html
from dash.dependencies import State, ALL, MATCH

from dash_extensions.enrich import Dash, Output, Input
from dash_extensions.enrich_composed import logger, Alias, ComposedComponent

# test all variants of component names and callbacks dependencies
_ids = ["my-id-simple", {"my-class": "my-class-index"}, {"id": "my-id-structured"}]
_aliases = {
    "my-alias-cc-simple": Alias("my-id-simple", "my-value"),
    "my-alias-cc-structured": Alias({"my-class": "my-class-index"}, "my-value"),
    "my-alias-simple": Alias("label-my-id-simple", "children"),
    "my-alias-structured": Alias({"my-class": "my-class-index", "is-label": True}, "children"),
}


def ids(text):
    return [
        f"{text}-{_id}" if isinstance(_id, str) else {f"{text}-{k}": v for k, v in _id.items()}
        for _id in _ids
    ]


def aliases(text):
    return {
        **{f"my-alias-cc-{i}": Alias(_id, "my-value") for i, _id in enumerate(ids(text))},
        **{f"my-alias-{i}": Alias(_id, "children") for i, _id in enumerate(ids(f"label-{text}"))},
    }


class A(ComposedComponent):
    _properties = ["my-state"]
    _aliases = aliases("a")

    def layout(self, **kwargs):
        return [B(id=id) for id in ids("a")] + [html.Label(id=id) for id in ids("label-a")]

    @classmethod
    def declare_callbacks(cls):
        @cls.callback(
            *(
                # add input on all children on ids
                [Input(component_id=id, component_property="hidden") for id in ids("a")]
                +
                # add state on all aliased properties
                [
                    State(component_id="self", component_property=prop)
                    for prop in aliases("a").keys()
                ]
                +
                # add state + output with MATCH (only one)
                [
                    State(component_id={k: MATCH for k in id}, component_property="my-value")
                    for id in ids("a")
                    if isinstance(id, dict)
                ][:1]
                + [
                    Output(component_id={k: MATCH for k in id}, component_property="my-value")
                    for id in ids("a")
                    if isinstance(id, dict)
                ][:1]
                +
                # add state with ALL
                [
                    State(component_id={k: ALL for k in id}, component_property="my-value")
                    for id in ids("a")
                    if isinstance(id, dict)
                ]
                +
                # add state with ALL
                [
                    State(component_id="self", component_property=prop)
                    for prop in aliases("a").keys()
                ]
            )
        )
        def a_callback(*args):
            print(args)


class B(ComposedComponent):
    _aliases = {"my-value": Alias("self", "children")}

    @classmethod
    def declare_callbacks(cls):
        @cls.callback(Input("self", "my-value"), Output("self", "n_clicks"))
        def b_callback(*args):
            print(args)


app = Dash()
app.layout = html.Div([A(id=id) for id in ids("core")])

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # app._setup_server()
    app.run_server(debug=True, dev_tools_hot_reload=True, port=8059)
