import time
import dash
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Input, Output
from dash_extensions.callback import CallbackPlumber, DiskPipeFactory

# Create example app.
app = dash.Dash(__name__, prevent_initial_callbacks=True)
app.layout = html.Div(
    [
        html.Button('Start', id='start', n_clicks=0), html.Button('Stop', id='stop', n_clicks=0),
        html.Div("Not running", id='progress'), html.Div("Last output = "), html.Div(id='result'),
        dcc.Interval(id='trigger', interval=1000),  html.Div(id='dummy')
    ]
)
# Create CallbackPlumber, use a folder on disk (server side) to save message in transit.
cp = CallbackPlumber(DiskPipeFactory("some_folder"))

@cp.piped_callback(Output('result', 'children'), [Input('start', 'n_clicks')])
def start_job(pipe, *args):
    n = 10
    for i in range(n): 
        pipe.send("progress", float(i)/float(n)*100)  # send progress updates to the client
        if pipe.receive("kill"):  # listen for (kill) signal(s) from the client
            return "No result (job killed)"  # return a value indicating that the job was killed
        time.sleep(0.1)  # sleep to emulate a long job
    return "The result!"  # return the result

@app.callback(Output('progress', 'children'), [Input('trigger', 'n_intervals')])
def update_progress(*args):
    progress = cp.receive("start_job", "progress")  # get latest progress value from "start_job"
    if progress is not None:
        return "Running (progress = {:.0f}%)".format(progress)
    return "Not running"

@app.callback(Output('dummy', 'children'), [Input('stop', 'n_clicks')])
def stop_job(*args):
    cp.send("start_job", "kill", True)  # send kill signal to "start_job"

cp.register(app)  # this call attaches the piped callback

if __name__ == '__main__':
    app.run_server()
