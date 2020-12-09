The purpose of this package is to provide various extensions to the Plotly Dash framework. It can be divided into four main blocks, 

* The `snippets` module, which contains a collection of utility functions
* The `javascript` module, which contains functionality to ease the interplay between Dash and JavaScript
* The `enrich` module, which contains various enriched versions of Dash components
* The `multipage` module, which contains utilities for multi page apps
* A number of custom components, e.g. the `Download` component

While the `snippets` module documentation will be limited to source code comments, the `enrich` module, the `javascript` module, and the custom components are documented below.

## Javascript

In Dash, component properties must be JSON serializable. However, many React components take JavaScript functions (or objects) as inputs, which can make it tedious to write Dash wrappers. To ease the process, `dash-extensions` implements a simple bridge for passing function handles (and other variables) as component properties. The `javascript` module is the Python side of the bridge, while the `dash-extensions` package [on npm](https://www.npmjs.com/package/dash-extensions) forms the JavaScript side. 

In the examples below, we will consider the `GeoJSON` component in `dash-leaflet==0.1.10`. The complete example apps are available in the [dash-leaflet documentation](http://dash-leaflet.herokuapp.com/#tutorials).

### JavaScript variables

Any JavaScript variable defined in the (global) window object can passed as a component property. Hence, if we create a .js file in the assets folder with the following content,

    window.myNamespace = Object.assign({}, window.myNamespace, {  
        mySubNamespace: {  
            pointToLayer: function(feature, latlng, context) {  
                return L.circleMarker(latlng)  
            }  
        }  
    });

the `pointToLayer` function of the `myNamespace.mySubNamespace` namespace can now be used as a component property,

    import dash_leaflet as dl
    from dash_extensions.javascript import Namespace
    ...
    ns = Namespace("myNamespace", "mySubNamespace")
    geojson = dl.GeoJSON(data=data, options=dict(pointToLayer=ns("pointToLayer")))

Note that this approach is not limited to function handles, but can be applied for any data type.

### Arrow functions

In some cases, it might be sufficient to wrap an object as an arrow function, i.e. a function that just returns the (constant) object. This behaviour can be achieved with the following syntax,

    import dash_leaflet as dl
    from dash_extensions.javascript import arrow_function
    ...
    geojson = dl.GeoJSON(hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')), ...)

## Enrichments

The `enrich` module provides a number of enrichments of the `Dash` object that can be enabled in a modular fashion. To get started, replace the `Dash` object by a `DashProxy` object and pass the desired transformations via the `transformations` keyword argument, 

    from enrich import DashProxy, TriggerTransform, GroupTransform, ServersideOutputTransform, NoOutputTransform
    
    app = DashProxy(transforms=[
        TriggerTransform(),  # enable use of Trigger objects
        GroupTransform(),  # enable use of the group keyword
        ServersideOutputTransform(),  # enable use of ServersideOutput objects
        NoOutputTransform(),  # enable callbacks without output
    ])

The `enrich` module also exposes a `Dash` object, which is a `DashProxy` object with all transformations loaded, i.e. a batteries included approach. However, it is recommended to load only the transforms are that actually used.

#### TriggerTransform

Makes it possible to use the `Trigger` component. Like an `Input`, it can trigger callbacks, but its value is not passed on to the callback,

    @app.callback(Output("output_id", "output_prop"), Trigger("button", "n_clicks"))
    def func():  # note that "n_clicks" is not included as an argument 

#### NoOutputTransform

Assigns dummy output automatically when a callback if declared without an `Output`,

    @app.callback(Trigger("button", "n_clicks"))  # note that the callback has no output

#### GroupTransform

Enables the `group` keyword, which makes it possible to bundle callbacks together. This feature serves as a work around for Dash not being able to target an output multiple times. Here is a small example,

    @app.callback(Output("log", "children"), Trigger("left", "n_clicks"), group="my_group") 
    def left():
        return "left"
        
    @app.callback(Output("log", "children"), Trigger("right", "n_clicks"), group="my_group") 
    def right():
        return "right"

#### ServersideOutputTransform

Makes it possible to use the `ServersideOutput` component. It works like a normal `Output`, but _keeps the data on the server_. By skipping the data transfer between server/client, the network overhead is reduced drastically, and the serialization to JSON can be avoided. Hence, you can now return complex objects, such as a pandas data frame, directly,

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

To enable the enrichments, replace the `Dash` object with a `DashProxy` object with the appropriate transformations applied, 

    from enrich import DashProxy, TriggerTransform, GroupTransform, ServersideOutputTransform, NoOutputTransform
    
    app = DashProxy(transforms=[
        TriggerTransform(),  # enable use of Trigger objects
        GroupTransform(),  # enable use of the group keyword
        ServersideOutputTransform(),  # enable use of ServersideOutput objects
        NoOutputTransform(),  # enable callbacks without output
    ])

## Components

The `multipage` module makes it easy to create multipage apps. Pages can be constructed explicitly with the following syntax,

    page = Page(id="page", label="A page", layout=layout, callbacks=callbacks)

where the `layout` function returns the page layout and the `callbacks` function registers any callbacks. Per default, all component ids are prefixed by the page id to avoid id collisions. It is also possible to construct a page from a module,

    page = module_to_page(module, id="module", label="A module")

if the module implements the `layout` and `callbacks` functions. Finally, any app constructed using a `DashProxy` object can be turned into a page,

    page = app_to_page(app, id="app", label="An app")

Once the pages have been constructed, they can be passed to a `PageCollection` object, which takes care of navigation. Hence a multipage app with a burger menu would be something like,

    # Create pages.
    pc = PageCollection(pages=[
        Page(id="page", label="A page", layout=layout, callbacks=callbacks),
        ...
    ])
    # Create app.
    app = DashProxy(suppress_callback_exceptions=True)
    app.layout = html.Div([make_burger(pc, effect="slide", position="right"), default_layout()])
    # Register callbacks.
    pc.navigation(app)
    pc.callbacks(app)

    if __name__ == '__main__':
        app.run_server(debug=False)

See the example folder on git for a complete example.

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
    # Create example app.
    app = dash.Dash(prevent_initial_callbacks=True)
    app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])
    
    @app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
    def func(n_nlicks):
        return send_data_frame(df.to_excel, "mydf.xls")
     
    if __name__ == '__main__':
        app.run_server()

### Monitor

The `Monitor` component makes it possible to monitor the state of child components. The most typical use case for this component is bi-directional synchronization of component properties. Here is a small example,

    import dash_core_components as dcc
    import dash_html_components as html
    from dash import Dash, no_update
    from dash.dependencies import Input, Output
    from dash.exceptions import PreventUpdate
    from dash_extensions import Monitor
    
    app = Dash()
    app.layout = html.Div(Monitor([
        dcc.Input(id="deg-fahrenheit", autoComplete="off", type="number"),
        dcc.Input(id="deg-celsius", autoComplete="off", type="number")],
        probes=dict(deg=[dict(id="deg-fahrenheit", prop="value"), 
                         dict(id="deg-celsius", prop="value")]), id="monitor")
    )
    
    @app.callback([Output("deg-fahrenheit", "value"), Output("deg-celsius", "value")], 
                  [Input("monitor", "data")])
    def sync_inputs(data):
        # Get value and trigger id from monitor.
        try:
            probe = data["deg"]
            trigger_id, value = probe["trigger"]["id"], float(probe["value"])
        except (TypeError, KeyError):
            raise PreventUpdate
        # Do the appropriate update.
        if trigger_id == "deg-fahrenheit":
            return no_update, (value - 32) * 5 / 9
        elif trigger_id == "deg-celsius":
            return value * 9 / 5 + 32, no_update
    
    
    if __name__ == '__main__':
        app.run_server(debug=False)

### Burger

The `Burger` component is a light wrapper of [react-burger-menu](https://github.com/negomi/react-burger-menu), which enables [cool interactive burger menus](https://negomi.github.io/react-burger-menu/).

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
