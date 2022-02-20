import dash
import dash_html_components as html
from html import unescape
from dash_extensions import DeferScript

mxgraph = r"{&quot;highlight&quot;:&quot;#0000ff&quot;,&quot;nav&quot;:true,&quot;resize&quot;:true,&quot;toolbar&quot;:&quot;zoom layers lightbox&quot;,&quot;edit&quot;:&quot;_blank&quot;,&quot;xml&quot;:&quot;&lt;mxfile host=\&quot;app.diagrams.net\&quot; modified=\&quot;2021-06-07T06:06:13.695Z\&quot; agent=\&quot;5.0 (Windows)\&quot; etag=\&quot;4lPJKNab0_B4ArwMh0-7\&quot; version=\&quot;14.7.6\&quot;&gt;&lt;diagram id=\&quot;YgMnHLNxFGq_Sfquzsd6\&quot; name=\&quot;Page-1\&quot;&gt;jZJNT4QwEIZ/DUcToOriVVw1JruJcjDxYho60iaFIaUs4K+3yJSPbDbZSzN95qPTdyZgadm/GF7LAwrQQRyKPmBPQRzvktidIxgmwB4IFEaJCUULyNQvEAyJtkpAswm0iNqqegtzrCrI7YZxY7Dbhv2g3r5a8wLOQJZzfU4/lbByoslduPBXUIX0L0cheUrugwk0kgvsVojtA5YaRDtZZZ+CHrXzukx5zxe8c2MGKntNgknk8bs8fsj3+KtuDhxP+HZDVU5ct/RhatYOXgGDbSVgLBIG7LGTykJW83z0dm7kjklbaneLnEnlwFjoL/YZzb93WwNYgjWDC6EEdkuC0cZEO7p3i/6RF1WutL8nxmnkxVx6UcUZJIy/LgP49622mO3/AA==&lt;/diagram&gt;&lt;/mxfile&gt;&quot;}"
app = dash.Dash(__name__)
app.layout = html.Div(
    [
        html.Div(className="mxgraph", style={"maxWidth": "100%"}, **{"data-mxgraph": unescape(mxgraph)}),
        DeferScript(src="https://viewer.diagrams.net/js/viewer-static.min.js"),
    ]
)

if __name__ == "__main__":
    app.run_server(port=9997)
