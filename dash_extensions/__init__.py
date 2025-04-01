from __future__ import print_function as _

import json
import os as _os
import sys as _sys

import dash as _dash

# noinspection PyUnresolvedReferences
from ._imports_ import *  # noqa: F401, F403
from ._imports_ import __all__

if not hasattr(_dash, "__plotly_dash") and not hasattr(_dash, "development"):
    print(
        "Dash was not successfully imported. "
        "Make sure you don't have a file "
        'named \n"dash.py" in your current directory.',
        file=_sys.stderr,
    )
    _sys.exit(1)

_basepath = _os.path.dirname(__file__)
_filepath = _os.path.abspath(_os.path.join(_basepath, "package-info.json"))
with open(_filepath) as f:
    package = json.load(f)

package_name = package["name"].replace(" ", "_").replace("-", "_")
__version__ = package["version"]

_current_path = _os.path.dirname(_os.path.abspath(__file__))

_this_module = _sys.modules[__name__]

async_resources = ["lottie", "mermaid"]
async_chunks = [f"async-{async_resource}" for async_resource in async_resources]

# Add shared chunks here.
shared_chunks = [
    f"{__name__}-shared",
]

# Collect all chunks (main, async, shared).
chunks = [__name__] + async_chunks + shared_chunks

# Add all chunks to the js_dist list.
_js_dist = []
_js_dist.extend(
    [
        {
            "relative_package_path": f"{chunk}.js",
            "external_url": f"https://unpkg.com/{package_name}@{__version__}/{__name__}/{chunk}.js",
            "namespace": package_name,
            "async": chunk != __name__,  # don't make the main bundle async
        }
        for chunk in chunks
    ]
)
_js_dist.extend(
    [
        {
            "relative_package_path": f"{chunk}.js.map",
            "external_url": f"https://unpkg.com/{package_name}@{__version__}/{__name__}/{chunk}.js.map",
            "namespace": package_name,
            "dynamic": True,
        }
        for chunk in chunks
    ]
)


# Similarly, collect CSS.
_css_dist = []

for _component in __all__:
    setattr(locals()[_component], "_js_dist", _js_dist)
    setattr(locals()[_component], "_css_dist", _css_dist)
