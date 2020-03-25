# dash-extensions

The purpose of the package is to provide various extensions to the Plotly Dash framework. It is essentially a collection of code snippets that i have been reusing across multiple projects.

### DashCallbackBlueprint

A known limitation of Dash is the inability to multiple callbacks to the same output. Hence the following code will **not** work,

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

Under the hood, the `DashCallbackBlueprint` class will merge the two callbacks into one and call invoke the appropriate function handler depending on the input trigger. In this simple case, the two callbacks could easily have been merged by hand. However, in more complex cases, the callback merging and control flow delegation can be cumbersome to implement by hand.