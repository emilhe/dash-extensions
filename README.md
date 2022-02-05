The purpose of this package is to provide various extensions to the Plotly Dash framework. It can be divided into five main blocks, 

* The `snippets` module, which contains a collection of utility functions
* The `javascript` module, which contains functionality to ease the interplay between Dash and JavaScript
* The `enrich` module, which contains various enriched versions of Dash components
* The `multipage` module, which contains utilities for multi page apps
* A number of custom components, e.g. the `Download` component

While the `snippets` module documentation will be limited to source code comments, the `javascript` module, the `enrich` module, the `multipage` module, and the custom components are documented below.

## Javascript

In Dash, component properties must be JSON serializable. However, many React components take JavaScript functions (or objects) as inputs, which can make it tedious to write Dash wrappers. To ease the process, `dash-extensions` implements a simple bridge for passing function handles (and other variables) as component properties. The `javascript` module is the Python side of the bridge, while the `dash-extensions` package [on npm](https://www.npmjs.com/package/dash-extensions) forms the JavaScript side. 

In the examples below, we will consider the `GeoJSON` component in `dash-leaflet==0.1.10`. The complete example apps are available in the [dash-leaflet documentation](http://dash-leaflet.herokuapp.com/#tutorials).

### JavaScript variables

Any JavaScript variable defined in the (global) window object can passed as a component property. Hence, if we create a .js file in the assets folder with the following content,

```js
window.myNamespace = Object.assign({}, window.myNamespace, {  
    mySubNamespace: {  
        pointToLayer: function(feature, latlng, context) {  
            return L.circleMarker(latlng)  
        }  
    }  
});
```

the `pointToLayer` function of the `myNamespace.mySubNamespace` namespace can now be used as a component property,

```python
import dash_leaflet as dl
from dash_extensions.javascript import Namespace
...
ns = Namespace("myNamespace", "mySubNamespace")
geojson = dl.GeoJSON(data=data, options=dict(pointToLayer=ns("pointToLayer")))
```

Note that this approach is not limited to function handles, but can be applied for any data type.

### Inline JavaScript

The `assign` function of the `javascript` module provides a more compact syntax where the JavaScript code is written as a string directly in the Python file. The previous example is thus reduced to,

```python
import dash_leaflet as dl
from dash_extensions.javascript import assign
...
point_to_layer = assign("function(feature, latlng, context) {return L.circleMarker(latlng);}")
geojson = dl.GeoJSON(data=data, options=dict(pointToLayer=point_to_layer))
```

without the need for creating any .js files manually. The syntax is particularly well suited for small JavaScript code snippets and/or examples. Note that under the hood, the inline functions are transpiled into a .js file, which is written to the assets folder.

### Arrow functions

In some cases, it might be sufficient to wrap an object as an arrow function, i.e. a function that just returns the (constant) object. This behaviour can be achieved with the following syntax,

```python
import dash_leaflet as dl
from dash_extensions.javascript import arrow_function
...
geojson = dl.GeoJSON(hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')), ...)
```

## Enrichments

The `enrich` module provides a number of enrichments of the `Dash` object that can be enabled in a modular fashion. To get started, replace the `Dash` object by a `DashProxy` object and pass the desired transformations via the `transforms` keyword argument, 

```python
from dash_extensions.enrich import DashProxy, TriggerTransform, MultiplexerTransform, ServersideOutputTransform, NoOutputTransform, BlockingCallbackTransform


app = DashProxy(transforms=[
    TriggerTransform(),  # enable use of Trigger objects
    MultiplexerTransform(),  # makes it possible to target an output multiple times in callbacks
    ServersideOutputTransform(),  # enable use of ServersideOutput objects
    NoOutputTransform(),  # enable callbacks without output
    BlockingCallbackTransform(),  # makes it possible to skip callback invocations while a callback is running 
])
```

The `enrich` module also exposes a `Dash` object, which is a `DashProxy` object with all transformations loaded, i.e. a batteries included approach. However, it is recommended to load only the transforms are that actually used.

NB: Transforms are not (yet) compatible the `long_callback` decorator. 

#### TriggerTransform

Makes it possible to use the `Trigger` component. Like an `Input`, it can trigger callbacks, but its value is not passed on to the callback,

```python
@app.callback(Output("output_id", "output_prop"), Trigger("button", "n_clicks"))
def func():  # note that "n_clicks" is not included as an argument 
```

#### MultiplexerTransform

Makes it possible to target an output by multiple callbacks, i.e enabling code like

```python
@app.callback(Output("log", "children"), Input("left", "n_clicks")) 
def left(_):
    return "left"

@app.callback(Output("log", "children"), Input("right", "n_clicks")) 
def right(_):
    return "right"
```

Under the hood, when `n` > 1 callbacks target the same element as output, _n_ `Store` elements are created, and the callbacks are redirect to target these intermediate outputs. Finally, a callback is added with the intermediate outputs as inputs and the original output as output. The strategy was contributed by [dwelch91](https://community.plotly.com/u/dwelch91/summary).

##### Wrappers, e.g. dcc.Loading

Since the `MultiplexerTransform` modifies the original callback to target a proxy component, wrappers (such as the `Loading` component) targeting the original output will not work as intended. If the output is static (i.e. not recreated by callbacks), the issue can avoided by injecting the proxy component next to the original output in the component tree,

```python
app = DashProxy(transforms=[MultiplexerTransform(proxy_location="inplace")])
```

If the output is not static, the recommended mitigation strategy is not to wrap to original ouput object, but to instead pass the wrapper(s) as proxy component wrappers,

```python
proxy_wrapper_map = {Output("log0", "children"): lambda proxy: dcc.Loading(proxy, type="dot")}
app = DashProxy(transforms=[MultiplexerTransform(proxy_wrapper_map)])
```

##### Know limitations

The `MultiplexerTransform` does not support the `MATCH` and `ALLSMALLER` wildcards. The `MultiplexerTransform` does not support `ServersideOutput`.

#### ServersideOutputTransform

Makes it possible to use the `ServersideOutput` component. It works like a normal `Output`, but _keeps the data on the server_. By skipping the data transfer between server/client, the network overhead is reduced drastically, and the serialization to JSON can be avoided. Hence, you can now return complex objects, such as a pandas data frame, directly,

```python
@app.callback(ServersideOutput("store", "data"), Input("left", "n_clicks")) 
def query(_):
    return pd.DataFrame(data=list(range(10)), columns=["value"])

@app.callback(Output("log", "children"), Input("store", "data")) 
def right(df):
    return df["value"].mean()
```
  
The reduced network overhead along with the avoided serialization to/from JSON can yield significant performance improvements, in particular for large data. Note that content of a `ServersideOutput` cannot be accessed by clientside callbacks. 
  
In addition, a new `memoize` keyword makes it possible to memoize the output of a callback. That is, the callback output is cached, and the cached result is returned when the same inputs occur again.

```python
@app.callback(ServersideOutput("store", "data"), Input("left", "n_clicks"), memoize=True) 
def query(_):
    return pd.DataFrame(data=list(range(10)), columns=["value"])
```

Used with a normal `Output`, this keyword is essentially equivalent to the `@flask_caching.memoize` decorator. For a `ServersideOutput`, the backend to do server side storage will also be used for memoization. Hence, you avoid saving each object two times, which would happen if the `@flask_caching.memoize` decorator was used with a `ServersideOutput`.

#### BlockingCallbackTransform

Makes it avoid invoking a callback _if it is already running_. The most typical use case is when polling data at an interval (say 1s) that is longer than the time it takes the callback to execute (say, 5s). Simply pass the `blocking` flag,

```python
@app.callback(Output("output", "children"), Input("trigger", "n_intervals"), blocking=True)
```

Under the hood, hidden dummy elements (client side) and client side callbacks keep track of whether a callback is already running or not. If it is already running, the Python callback is not invoked.

#### TriggerTransform

Makes it possible to use the `Trigger` component. Like an `Input`, it can trigger callbacks, but its value is not passed on to the callback,

```python
@app.callback(Output("output_id", "output_prop"), Trigger("button", "n_clicks"))
def func():  # note that "n_clicks" is not included as an argument 
```

## Multipage

The `multipage` module makes it easy to create multipage apps. Pages can be constructed explicitly with the following syntax,

```python
page = Page(id="page", label="A page", layout=layout, callbacks=callbacks)
```

where the `layout` function returns the page layout and the `callbacks` function registers any callbacks. Per default, all component ids are prefixed by the page id to avoid id collisions. It is also possible to construct a page from a module,

```python
page = module_to_page(module, id="module", label="A module")
```

if the module implements the `layout` and `callbacks` functions. Finally, any app constructed using a `DashProxy` object can be turned into a page,

```python
page = app_to_page(app, id="app", label="An app")
```

Once the pages have been constructed, they can be passed to a `PageCollection` object, which takes care of navigation. Hence a multipage app with a simple menu would be something like,

```python
# Create pages.
pc = PageCollection(pages=[
    Page(id="page", label="A page", layout=layout, callbacks=callbacks),
    ...
])
# Create app.
app = DashProxy(suppress_callback_exceptions=True)
app.layout = html.Div(simple_menu(pc) + [html.Div(id=CONTENT_ID), dcc.Location(id=URL_ID)])
# Register callbacks.
pc.navigation(app)
pc.callbacks(app)
```

The complete example is available [in the examples folder](https://github.com/thedirtyfew/dash-extensions/blob/master/examples/multipage_app.py).

## Dataiku

The `dataiku` module provides a few utility functions to ease the integration of Dash apps in [dataiku](https://www.dataiku.com/) 8.x (from 9.0, an official Dash integration is provided). To get started, create a standard web app. Make sure that the selected code environment (can be configured in the Settings tab) has the following packages installed,

```
dash==1.18.1
dash-extensions==0.0.44
```

Replace the content of the HTML tab with

```html
<head>
    <script type="text/javascript" src="https://cdn.jsdelivr.net/gh/thedirtyfew/dash-extensions@0.0.44/snippets/dataiku.js"></script>
</head>
```

and clear the JS and CSS tabs (unless you the JS/CSS code). Finally, go to the Python tab and replace the content with

```python
from dash import Dash, html
from dash_extensions.dataiku import setup_dataiku

# Path for storing app configuration (must be writeable).
config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
# Create a small example app.
dash_app = Dash(__name__, **setup_dataiku(app, config_path))
dash_app.layout = html.Div("Hello from Dash!")
```

After clicking save, you should see the text `Hello from Dash!` in the preview window (a backend restart might be required). Congratulations! You have created you first Dash app in dataiku.

## Components

The components listed here can be used in the `layout` of your Dash app. 

### EventSource

The `EventSource` component makes it possible to liten to [server sent events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events). Simply point the component to the appropriate server via the `url` prop, and create a callback targeting the `message` property,

```python
from dash import Dash, html, Input, Output, dcc
from dash_extensions import EventSource

# The url of server that emits the events.
sse_url = "http://127.0.0.1:8000"
# Create small example app.
app = Dash(__name__)
app.layout = html.Div([dcc.Graph(id="graph"), EventSource(id="sse", url=sse_url)])
# You could also use a normal callback, but client side callbacks yield better performance.
app.clientside_callback(
    """
    function(val) {
        values = val ? JSON.parse(val) : []
        return {data: [{y: values , type: "scatter"}]}
    }
    """,
    Output("graph", "figure"),
    Input("sse", "message"),
)

if __name__ == "__main__":
    app.run_server()
```

The above example assumes that a server running on `http://127.0.0.1:8000` is emitting events to populate the graph. There is no specific requirement on the type of server, but here is a small example in Python,

```python
import asyncio
import random
import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

app = Starlette(middleware=[Middleware(CORSMiddleware, allow_origins=['*'])])

async def numbers():
    while True:
        await asyncio.sleep(1)
        yield [random.randrange(200, 1000) for _ in range(10)]

@app.route("/")
async def sse(request):
    generator = numbers()
    return EventSourceResponse(generator)

if __name__ == "__main__":
    uvicorn.run(app, port=8000)
```

that yields random numbers in a format compatible with the client example app above. The `EventSource` component has been contributed by [snehilvj](https://github.com/snehilvj).

### EventListener

The `EventListener` component makes it possible to listen to (arbitrary) JavaScript events. Simply wrap the relevant components in an `EventListener` component, specify which event(s) to subscribe to, and what event properties to send back to Dash,

```python
from dash import Dash, html, Input, Output, State
from dash_extensions import EventListener

# JavaScript event(s) that we want to listen to and what properties to collect.
event = {"event": "click", "props": ["srcElement.className", "srcElement.innerText"]}
# Create small example app
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    EventListener(
        html.Div("Click here!", id="click_here", className="stuff"),
        events=[event], logging=True, id="el"
    ),
    html.Div(id="log")
])

@app.callback(Output("log", "children"), Input("el", "n_events"), State("el", "event"))
def click_event(n_events, e):
    return ",".join(f"{prop} is '{e[prop]}' " for prop in event["props"]) + f" (number of clicks is {n_events})"

if __name__ == "__main__":
    app.run_server()
```

Note that if the relevant events are already exposed as properties in Dash, there is no benefit of using the `EventListener` component. The intended usage of the `EventListener` component is when this is _not_ the case. Say that you need to listen to double-click events, but the Dash component only exposes a (single) click property; or some data that you need is not propagated from the JavaScript layer. In this case, the `EventListener` component makes it possible to achieve the desired behaviour without editing the component source code (i.e. the JavaScript code).

### Purify

The `Purify` component makes it possible to render HTML, MathML, and SVG. Typically, such rendering is prone to XSS vulnerabilities. These risks are mitigated by sanitizing the html input using the [DOMPurify](https://github.com/cure53/DOMPurify) library. Here is a minimal example,

```python
from dash import Dash
from dash_extensions import Purify

app = Dash()
app.layout = Purify("This is <b>html</b>")

if __name__ == "__main__":
    app.run_server()
```

### WebSocket

The `WebSocket` component enables communication via _websockets_ in Dash. Simply add the `WebSocket` component to the layout and set the `url` property to the websocket endpoint. Messages can be send by writing to the `send` property, and received messages are written to the `message` property. Here is a small example,

```python
from dash import Dash, html, dcc, Input, Output
from dash_extensions import WebSocket

# Create example app.
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([
    dcc.Input(id="input", autoComplete="off"), html.Div(id="message"),
    WebSocket(url="wss://echo.websocket.org", id="ws")
])

@app.callback(Output("ws", "send"), [Input("input", "value")])
def send(value):
    return value

@app.callback(Output("message", "children"), [Input("ws", "message")])
def message(e):
    return f"Response from websocket: {e['data']}"

if __name__ == '__main__':
    app.run_server()
```

Websockets make it possible to solve a number of cases, which can otherwise be challenging in Dash, e.g.

* Updating client content without server interaction
* Pushing updates from the server to the client(s)
* Running long processes asynchronously

Examples can be found in the `examples` folder.

### Download

The `Download` component provides an easy way to download data from a Dash application. Simply add the `Download` component to the app layout, and add a callback which targets its `data` property. Here is a small example,

```python
from dash import Dash, html, Output, Input
from dash_extensions import Download

app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])

@app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
def func(n_clicks):
    return dict(content="Hello world!", filename="hello.txt")

if __name__ == '__main__':
    app.run_server()
```

To ease downloading files, a `send_file` utility method is included,

```python
from dash import Dash, html, Output, Input
from dash_extensions import Download
from dash_extensions.snippets import send_file

app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])

@app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
def func(n_clicks):
    return send_file("/home/emher/Documents/Untitled.png")

if __name__ == '__main__':
    app.run_server()
```

To ease downloading data frames (which seems to be a common use case for Dash users), a `send_data_frame` utility method is also included,

```python
import pandas as pd
from dash import Dash, html, Input, Output
from dash_extensions import Download
from dash_extensions.snippets import send_data_frame

# Example data.
df = pd.DataFrame({'a': [1, 2, 3, 4], 'b': [2, 1, 5, 6], 'c': ['x', 'x', 'y', 'y']})
# Create example app.
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])

@app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
def func(n_nlicks):
    return send_data_frame(df.to_excel, "mydf.xls")

if __name__ == '__main__':
    app.run_server()
```

Finally, a `send_bytes`  utility method is included to make it easy to download in-memory objects that support writing to BytesIO. Typical use cases are excel files,

```python
import numpy as np
import pandas as pd
from dash import Dash, html, Output, Input
from dash_extensions import Download
from dash_extensions.snippets import send_bytes

# Example data.
data = np.column_stack((np.arange(10), np.arange(10) * 2))
df = pd.DataFrame(columns=["a column", "another column"], data=data)
# Create example app.
app = Dash(prevent_initial_callbacks=True)
app.layout = html.Div([html.Button("Download xlsx", id="btn"), Download(id="download")])

@app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
def generate_xlsx(n_nlicks):

    def to_xlsx(bytes_io):
        xslx_writer = pd.ExcelWriter(bytes_io, engine="xlsxwriter")
        df.to_excel(xslx_writer, index=False, sheet_name="sheet1")
        xslx_writer.save()

    return send_bytes(to_xlsx, "some_name.xlsx")


if __name__ == '__main__':
    app.run_server()
```

and figure objects,

```python
import plotly.graph_objects as go
from dash import Dash, html, Input, Output
from dash_extensions import Download
from dash_extensions.snippets import send_bytes

app = Dash()
app.layout = html.Div([html.Button("Download", id="btn"), Download(id="download")])

@app.callback(Output("download", "data"), [Input("btn", "n_clicks")])
def download(n_clicks):
    f = go.Figure()
    return send_bytes(f.write_image, "figure.png")

if __name__ == '__main__':
    app.run_server()
```

### Mermaid

The `Mermaid` component is a light wrapper of [react-mermaid2](https://github.com/e-attestations/react-mermaid2), which makes it possible to [draw flow diagrams](https://github.com/mermaid-js/mermaid). Here is a small example,

```python
from dash import Dash
from dash_extensions import Mermaid

chart = """
graph TD;
A-->B;
A-->C;
B-->D;
C-->D;
"""
app = Dash()
app.layout = Mermaid(chart=chart)

if __name__ == "__main__":
    app.run_server()
```

### DeferScript

The `DeferScript` component makes it possible to defer the loading of javascript code, which is often required to render dynamic content. One such example is [draw.io](https://app.diagrams.net/),

```python
from dash import Dash, html
from html import unescape
from dash_extensions import DeferScript


mxgraph = r'{&quot;highlight&quot;:&quot;#0000ff&quot;,&quot;nav&quot;:true,&quot;resize&quot;:true,&quot;toolbar&quot;:&quot;zoom layers lightbox&quot;,&quot;edit&quot;:&quot;_blank&quot;,&quot;xml&quot;:&quot;&lt;mxfile host=\&quot;app.diagrams.net\&quot; modified=\&quot;2021-06-07T06:06:13.695Z\&quot; agent=\&quot;5.0 (Windows)\&quot; etag=\&quot;4lPJKNab0_B4ArwMh0-7\&quot; version=\&quot;14.7.6\&quot;&gt;&lt;diagram id=\&quot;YgMnHLNxFGq_Sfquzsd6\&quot; name=\&quot;Page-1\&quot;&gt;jZJNT4QwEIZ/DUcToOriVVw1JruJcjDxYho60iaFIaUs4K+3yJSPbDbZSzN95qPTdyZgadm/GF7LAwrQQRyKPmBPQRzvktidIxgmwB4IFEaJCUULyNQvEAyJtkpAswm0iNqqegtzrCrI7YZxY7Dbhv2g3r5a8wLOQJZzfU4/lbByoslduPBXUIX0L0cheUrugwk0kgvsVojtA5YaRDtZZZ+CHrXzukx5zxe8c2MGKntNgknk8bs8fsj3+KtuDhxP+HZDVU5ct/RhatYOXgGDbSVgLBIG7LGTykJW83z0dm7kjklbaneLnEnlwFjoL/YZzb93WwNYgjWDC6EEdkuC0cZEO7p3i/6RF1WutL8nxmnkxVx6UcUZJIy/LgP49622mO3/AA==&lt;/diagram&gt;&lt;/mxfile&gt;&quot;}'
app = Dash(__name__)
app.layout = html.Div([
    html.Div(className='mxgraph', style={"maxWidth": "100%"}, **{'data-mxgraph': unescape(mxgraph)}),
    DeferScript(src='https://viewer.diagrams.net/js/viewer-static.min.js')
])

if __name__ == '__main__':
    app.run_server()
```

### BeforeAfter

The `BeforeAfter` component is a light wrapper of [react-before-after-slider](https://github.com/transitive-bullshit/react-before-after-slider/), which makes it possible to [highlight differences between two images](https://transitive-bullshit.github.io/react-before-after-slider/). Here is a small example,

```python
from dash import Dash, html
from dash_extensions import BeforeAfter

app = Dash()
app.layout = html.Div([
    BeforeAfter(before="assets/lena_bw.png", after="assets/lena_color.png", width=512, height=512)
])

if __name__ == '__main__':
    app.run_server()
```

### Ticker

The `Ticker` component is a light wrapper of [react-ticker](https://github.com/AndreasFaust/react-ticker), which makes it easy to show [moving text](https://andreasfaust.github.io/react-ticker/). Here is a small example,

```python
from dash import Dash, html
from dash_extensions import Ticker

app = Dash(__name__)
app.layout = html.Div(Ticker([html.Div("Some text")], direction="toRight"))

if __name__ == '__main__':
    app.run_server()
 ```

### Lottie

The `Lottie` component makes it possible to run Lottie animations in Dash. Here is a small example,

```python
from dash import Dash, html
import dash_extensions as de

# Setup options.
url = "https://assets9.lottiefiles.com/packages/lf20_YXD37q.json"
options = dict(loop=True, autoplay=True, rendererSettings=dict(preserveAspectRatio='xMidYMid slice'))
# Create example app.
app = Dash(__name__)
app.layout = html.Div(de.Lottie(options=options, width="25%", height="25%", url=url))

if __name__ == '__main__':
    app.run_server()
```

### Burger

The `Burger` component is a light wrapper of [react-burger-menu](https://github.com/negomi/react-burger-menu), which enables [cool interactive burger menus](https://negomi.github.io/react-burger-menu/). Here is a small example,

```python
from dash import Dash, html
from dash_extensions import Burger


def link_element(icon, text):
    return html.A(children=[html.I(className=icon), html.Span(text)], href=f"/{text}",
                  className="bm-item", style={"display": "block"})


# Example CSS from the original demo.
external_css = [
    "https://negomi.github.io/react-burger-menu/example.css",
    "https://negomi.github.io/react-burger-menu/normalize.css",
    "https://negomi.github.io/react-burger-menu/fonts/font-awesome-4.2.0/css/font-awesome.min.css"
]
# Create example app.
app = Dash(external_stylesheets=external_css)
app.layout = html.Div([
    Burger(children=[
        html.Nav(children=[
            link_element("fa fa-fw fa-star-o", "Favorites"),
            link_element("fa fa-fw fa-bell-o", "Alerts"),
            link_element("fa fa-fw fa-envelope-o", "Messages"),
            link_element("fa fa-fw fa-comment-o", "Comments"),
            link_element("fa fa-fw fa-bar-chart-o", "Analytics"),
            link_element("fa fa-fw fa-newspaper-o", "Reading List")
        ], className="bm-item-list", style={"height": "100%"})
    ], id="slide"),
    html.Main("Hello world!", style={"width": "100%", "height": "100vh"}, id="main")
], id="outer-container", style={"height": "100%"})

if __name__ == '__main__':
    app.run_server()
```

### Keyboard

The `Keyboard` component makes it possible to capture keyboard events at the document level. Here is a small example,

```python
import json
from dash import Dash, html, Output, Input, State
from dash_extensions import Keyboard

app = Dash()
app.layout = html.Div([Keyboard(id="keyboard"), html.Div(id="output")])

@app.callback(
    Output("output", "children"), 
    [Input("keyboard", "n_keydowns")],
    [State("keyboard", "keydown")],
)
def keydown(n_keydowns, event):
    return json.dumps(event)


if __name__ == '__main__':
    app.run_server()
```

### Monitor

The `Monitor` component makes it possible to monitor the state of child components. The most typical use case for this component is bi-directional synchronization of component properties. Here is a small example,

```python
from dash import Dash, html, dcc, no_update, Input, Output
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
```
