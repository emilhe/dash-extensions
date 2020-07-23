from dash_extensions.callback import DiskCache, CallbackBlueprint
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flask import session, Flask
import time
import os

# region TO BE MOVED

import contextlib
import os
import secrets

class CallbackPipe(CallbackBlueprint):

    # TODO: Add support for other types of cache.

    def __init__(self, cache_dir):
        super().__init__()
        self.cache_dir = cache_dir
        self.magic_callbacks = []

    def _get_cache(self, func, **kwargs):
        # Create unique session id.
        if not session.get("magic_id"):
            session["magic_id"] = secrets.token_urlsafe(16)
        # Create cache object.
        return DiskCache(os.path.join(self.cache_dir, session.get("magic_id"), func), **kwargs)

    # def get(self, func):
    #     cache = self._get_cache(func, makedirs=False)
    #     return None if cache.nuked else cache

    def load(self, func, key):
        return self._get_cache(func).load(key)

    def dump(self, value, func, key):
        return self._get_cache(func).dump(value, key)


    @contextlib.contextmanager
    def open(self, name):
        cache = self._get_cache(name)
        yield cache
        cache.nuke()  # or whatever you need to do at exit


    def magic_callback(self, outputs, inputs, states=None):
        # Save index to keep tract of which callback to cache.
        self.magic_callbacks.append(len(self.callbacks))
        # Save the callback itself.
        return self.callback(outputs, inputs, states)

# endregion

app = dash.Dash(__name__, prevent_initial_callbacks=True)
app.server.secret_key = secrets.token_urlsafe(16)  # this line MUST be included
app.layout = html.Div(
    [
        html.Button('Start long process', id='start', n_clicks=0),
        html.Button('Stop long process', id='stop', n_clicks=0),
        html.Div(id='result'), html.Div(id='progress'), html.Div(id="dummy"),
        dcc.Interval(id='trigger')
    ]
)
cp = CallbackPipe(cache_dir="tmp")


@app.callback(Output('result', 'children'), [Input('start', 'n_clicks')])
def run_job(n_clicks):
    with cp.open("run_job") as pipe:  # open a pipe to enable communication with other callbacks
        n = 10
        for i in range(n):
            pipe.dump(float(i)/float(n)*100, "progress")  # send progress updates to the client
            if pipe.load("kill"):  # listen for (kill) signal(s) from the client
                return "Job stopped"
            time.sleep(1)  # sleep to emulate a long job
    return "Job completed"


@app.callback(Output('progress', 'children'), [Input('trigger', 'n_intervals')])
def update_progress(n_intervals):
    progress = cp.load("run_job", "progress") 
    if progress is not None:
        return "Progress is {}%".format(progress)


@app.callback(Output('dummy', 'children'), [Input('stop', 'n_clicks')])
def stop_job(n_clicks):
    cp.dump(True, "run_job", "kill")


if __name__ == '__main__':
    app.run_server()
