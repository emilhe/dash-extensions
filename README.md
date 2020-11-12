The purpose of this package is to provide various extensions to the Plotly Dash framework. It can be divided into three main blocks, 

* The `snippets` module, which contains a collection of utility functions
* The `enrich` module, which contains various enriched versions of Dash components
* A number of custom components, e.g. the `Download` component

While the `snippets` module documentation will be limited to source code comments, the `enrich` module and the custom components are documented below.

## Enrichments

At the time of writing, the following enrichments (as compared to Dash 1.14.0) have been implemented,

* Ordering and form (single element versus list) of (`Output`, `Input`, `State`) does not matter. Hence, you could do this,

        @app.callback(Input("input_id", "input_prop"), Output("output_id", "output_prop"))

* A new `Trigger` component has been added. Like an `Input`, it can trigger callbacks, but its value is not passed on to the callback,

        @app.callback(Output("output_id", "output_prop"), Trigger("button", "n_clicks"))
        def func():  # note that "n_clicks" is not included as an argument 

* It is now possible to have callbacks without an `Output`,

        @app.callback(Trigger("button", "n_clicks"))  # note that the callback has no output

* A new `group` keyword makes it possible to bundle callbacks together. This feature serves as a work around for Dash not being able to target an output multiple times. Here is a small example,

        @app.callback(Output("log", "children"), Trigger("left", "n_clicks"), group="my_group") 
        def left():
            return "left"
            
        @app.callback(Output("log", "children"), Trigger("right", "n_clicks"), group="my_group") 
        def right():
            return "right"

* A new `ServersideOutput` component has been added. It works like a normal `Output`, but _keeps the data on the server_. By skipping the data transfer between server/client, the network overhead is reduced drastically, and the serialization to JSON can be avoided. Hence, you can now return complex objects, such as a pandas data frame, directly,

        @app.callback(ServersideOutput("store", "data"), Trigger("left", "n_clicks")) 
        def query():
            return pd.DataFrame(data=list(range(10)), columns=["value"])
            
        @app.callback(Output("log", "children"), Input("store", "data")) 
        def right(df):
            return df["value"].mean()
  
  The reduced network overhead along with the avoided serialization to/from JSON can yield significant performance improvements, in particular for large data. Note that content of a `ServersideOutput` cannot be accessed by clientside callbacks. 
  
* A new `memoize` keyword makes it possible to memoize the output of a callback. That is, the callback output is cached, and the cached result is returned when the same inputs occur again.

        @app.callback(ServersideOutput("store", "data"), Trigger("left", "n_clicks"), memoize=True) 
        def query():
            return pd.DataFrame(data=list(range(10)), columns=["value"])

    Used with a normal `Output`, this keyword is essentially equivalent to the `@flask_caching.memoize` decorator. For a `ServersideOutput`, the backend to do server side storage will also be used for memoization. Hence you avoid saving each object two times, which would happen if the `@flask_caching.memoize` decorator was used with a `ServersideOutput`.
            
To enable the enrichments, simply replace the imports of the `Dash` object and the (`Output`, `Input`, `State`) objects with their enriched counterparts,

    from dash_extensions.enrich import Dash, Output, Input, State

The syntax in the `enrich` module should be considered alpha stage. It might change without notice.

## Composed Components

With the ComposedComponentMixin, it is possible to combine & encapsulate a set of components to create a new component, all in pure python.

For example, here we make an EnhanceSlider, based on a Div, that will expose only two properties ('info' and 'size').

```python
import dash
import dash_core_components as dcc
import dash_html_components as html

from dash_extensions.enrich import Dash, Output, Input, State
from dash_extensions.enrich_composed import ComposedComponentMixin, Alias


class EnhanceSlider(ComposedComponentMixin, html.Div):
    """Example component enhancing a standard slider with an input field, both being updatable and kept in sync.

    Inspired by https://community.plotly.com/t/problem-with-circular-callbacks-slider-changes-input-and-input-changes-slider/39685/2
    """

    # define the alias that will expose as the "value" property of the EnhanceSlider the value of the input
    _aliases = {"value": Alias("input", "value")}

    def layout(self, value):
        return html.Div(
            id="holder",
            children=[
                dcc.Slider(id="slider", min=0, max=100, value=0),
                dcc.Input(id="input", value=0),
            ],
        )

    @classmethod
    def declare_callbacks(cls):
        """Declare the callback that handles the sync of the two fields."""

        @cls.callback(
            Input("slider", "value"),
            Input("input", "value"),
            State("slider", "id"),
            State("input", "id"),
            Output("holder", "children"),
        )
        def sync_values(slider, input, slider_id, input_id):
            # get the dependency that has triggered the callback
            trigger_id = dash.callback_context.triggered[0]["prop_id"]

            try:
                # get the value of the triggered input
                value = int(dash.callback_context.inputs[trigger_id])
            except KeyError:
                # happens in case of trigger_id="." (initial trigger)
                return dash.no_update

            # overwrite the components with new components
            # reusing the ids of the initial components (as ids have been mangled)
            return [
                dcc.Slider(id=slider_id, min=0, max=100, value=value),
                dcc.Input(id=input_id, value=value),
            ]
```

This component can be used now as if it was a new Dash component with two properties:

```python
app = Dash(
    __name__,
    title="Enhance slider demo",
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
)

app.layout = html.Div(
    [
        html.H1("Enhanced Slider demo"),
        html.P(
            "The EnhanceSlider component proposes both a slider "
            "and an input to define a value, with both fields synchronised."
        ),
        html.Div(id="inject"),
        EnhanceSlider(id="my-slider"),
    ]
)


@app.callback(Input("my-slider", "value"), Output("inject", "children"))
def refresh_label(value):
    return f"The value of the enhanced slider is {value}"
```


## Components

The components listed here can be used in the `layout` of your Dash app. 

### Download

The `Download` component provides an easy way to download data from a Dash application. Simply add the `Download` component to the app layout, and add a callback which targets its `data` property. Here is a small example,

    import dash
    import dash_html_components as html
    from dash.dependencies import Output, Input
    from dash_extensions import Download
    
    app = dash.Dash(prevent_initial_callbacks=True)
    app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])
    
    @app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
    def func(n_clicks):
        return dict(content="Hello world!", filename="hello.txt")
    
    if __name__ == '__main__':
        app.run_server()

To ease downloading files, a `send_file` utility method is included,

    import dash
    import dash_html_components as html  
    from dash.dependencies import Output, Input
    from dash_extensions import Download
    from dash_extensions.snippets import send_file
    
    app = dash.Dash(prevent_initial_callbacks=True)
    app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])
   
    @app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
    def func(n_clicks):
        return send_file("/home/emher/Documents/Untitled.png")
   
    if __name__ == '__main__':
        app.run_server()

To ease downloading data frames (which seems to be a common use case for Dash users), a `send_data_frame` utility method is also included,

    import dash
    import pandas as pd
    import dash_html_components as html
    
    from dash.dependencies import Output, Input
    from dash_extensions import Download
    from dash_extensions.snippets import send_data_frame
    
    # Example data.
    df = pd.DataFrame({'a': [1, 2, 3, 4], 'b': [2, 1, 5, 6], 'c': ['x', 'x', 'y', 'y']})
    # Create app.
    app = dash.Dash(prevent_initial_callbacks=True)
    app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])
    
    @app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
    def func(n_nlicks):
        return send_data_frame(df.to_excel, "mydf.xls")
     
    if __name__ == '__main__':
        app.run_server()


### Lottie

The `Lottie` component makes it possible to run Lottie animations in Dash. Here is a small example,

    import dash
    import dash_html_components as html
    import dash_extensions as de
    
    # Setup options.
    url = "https://assets9.lottiefiles.com/packages/lf20_YXD37q.json"
    options = dict(loop=True, autoplay=True, rendererSettings=dict(preserveAspectRatio='xMidYMid slice'))
    # Create example app.
    app = dash.Dash(__name__)
    app.layout = html.Div(de.Lottie(options=options, width="25%", height="25%", url=url))
    
    if __name__ == '__main__':
        app.run_server()


### Keyboard

The `Keyboard` component makes it possible to capture keyboard events at the document level. Here is a small example,

    import dash
    import dash_html_components as html
    import json
    
    from dash.dependencies import Output, Input
    from dash_extensions import Keyboard
    
    app = dash.Dash()
    app.layout = html.Div([Keyboard(id="keyboard"), html.Div(id="output")])
    
    
    @app.callback(Output("output", "children"), [Input("keyboard", "keydown")])
    def keydown(event):
        return json.dumps(event)
    
    
    if __name__ == '__main__':
        app.run_server()
