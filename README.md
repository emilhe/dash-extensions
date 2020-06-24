# dash-extensions

The purpose of this package is to provide various extensions to the Plotly Dash framework. It is essentially a collection of code snippets that i have been reusing across multiple projects.

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


### DashCallbackBlueprint

A known limitation of Dash is the inability to assign multiple callbacks to the same output. Hence the following code will **not** work,

    import dash
    import dash_html_components as html
    from dash.dependencies import Output, Input
    
    app = dash.Dash()
    app.layout = html.Div([html.Button("Button 1", id="btn1"), html.Button("Button 2", id="btn2"), html.Div(id="div")])
    
    
    @app.callback(Output("div", "children"), [Input("btn1", "n_clicks")])
    def click_btn1(n_clicks):
        return "You clicked btn1"
    
    
    @app.callback(Output("div", "children"), [Input("btn2", "n_clicks")])
    def click_btn2(n_clicks):
        return "You clicked btn2"
    
    
    if __name__ == '__main__':
        app.run_server()

Specifically, a dash.exceptions.DuplicateCallbackOutput exception will be raised as an attempt is made to assign the output `Output("div", "children")` a second time. 

To address this problem, this package provides the `DashCallbackBlueprint` class. It acts as a proxy for the Dash application during callback registration, but unlike the Dash application, it supports assignment of multiple callbacks to the same output. When all callbacks have been assigned, the blueprint is registered on the Dash application,

    import dash
    import dash_html_components as html
    from dash.dependencies import Output, Input
    from dash_extensions.callback import DashCallbackBlueprint
    
        
    app = dash.Dash()
    app.layout = html.Div([html.Button("Button 1", id="btn1"), html.Button("Button 2", id="btn2"), html.Div(id="div")])
    dcb = DashCallbackBlueprint() 
    
    
    @dcb.callback(Output("div", "children"), [Input("btn1", "n_clicks")])
    def click_btn1(n_clicks):
        return "You clicked btn1"
    
    
    @dcb.callback(Output("div", "children"), [Input("btn2", "n_clicks")]) 
    def click_btn2(n_clicks):
        return "You clicked btn2"
    
    
    dcb.register(app)  
    
    if __name__ == '__main__':
        app.run_server()

Under the hood, the two callbacks are merged into one with the appropriate function handler invoked depending on the input trigger. In this simple case, the two callbacks could easily have been merged by hand. However, in more complex cases, the callback merging and control flow delegation can be cumbersome to implement by hand.