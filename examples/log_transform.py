import dash_mantine_components as dmc
from dash_extensions.enrich import Output, Input, html, DashProxy, LogTransform, DashLogger

app = DashProxy(transforms=[LogTransform()], prevent_initial_callbacks=True)
app.layout = html.Div([dmc.Button("Run", id="btn"), dmc.Text(id="txt")])


@app.callback(Output("txt", "children"), Input("btn", "n_clicks"), log=True)
def info_stuff(n_clicks, logger: DashLogger):
    logger.info("Here goes some info")
    logger.info("Here goes some more info")
    logger.warning("This is a warning")
    logger.info("Even more info")
    logger.error("Some error occurred")
    return f"Run number {n_clicks} completed"


app.run_server(port=7879)
