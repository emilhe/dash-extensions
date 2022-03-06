import os.path

from dash_extensions.javascript import arrow_function, assign

# A few test stubs.
js_func = "function(feature, latlng, context) {return L.circleMarker(latlng);}"
expected = """window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, latlng, context) {
            return L.circleMarker(latlng);
        }
    }
});"""


def test_namespace():
    # Clear asset if present.
    asset_path = "assets/dashExtensions_default.js"
    if os.path.isfile(asset_path):
        os.remove(asset_path)
    # Check how the variable looks.
    ptl = assign(js_func)
    assert ptl == {'variable': 'dashExtensions.default.function0'}
    # Check that assets are written.
    with open(asset_path, 'r') as f:
        assets_content = f.read()
    assert assets_content == expected


def test_arrow_function():
    af = arrow_function("x")
    assert af == {"arrow": "x"}
