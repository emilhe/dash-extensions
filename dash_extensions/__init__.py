from __future__ import print_function as _

import os as _os
import sys as _sys
import json

import dash as _dash
# from . import assets  # noqa

# noinspection PyUnresolvedReferences
from ._imports_ import *
from ._imports_ import __all__

if not hasattr(_dash, 'development'):
    print('Dash was not successfully imported. '
          'Make sure you don\'t have a file '
          'named \n"dash.py" in your current directory.', file=_sys.stderr)
    _sys.exit(1)

_basepath = _os.path.dirname(__file__)
_filepath = _os.path.abspath(_os.path.join(_basepath, 'package-info.json'))
with open(_filepath) as f:
    package = json.load(f)

package_name = package['name'].replace(' ', '_').replace('-', '_')
__version__ = package['version']

_current_path = _os.path.dirname(_os.path.abspath(__file__))

_this_module = _sys.modules[__name__]

_css_dist = []
_js_dist = [
    {
        'relative_package_path': 'dash_extensions.min.js',
        'namespace': package_name
    },
    {
        'relative_package_path': 'dash_extensions.min.js.map',
        'namespace': package_name,
        'dynamic': True
    }
]

# Prepare per-chunk js imports.
_chunk_map = {
    "Lottie": ["lottie"],
    "Burger": ["burger"],
    "Mermaid": ["mermaid"]
}
_chunk_js_dist_map = {}
for _component in _chunk_map:
    _chunk_js_dist_map[_component] = []
    for entry in _chunk_map[_component]:
        _chunk_js_dist_map[_component] += [
            {
                'relative_package_path': f'async-{entry}.js',
                'namespace': package_name
            },
            {
                'relative_package_path': f'async-{entry}.js.map',
                'namespace': package_name,
                'dynamic': True
            }
        ]

# Add chunks to respective components so that they only load when the component is imported.
for _component in __all__:
    _component_js_dist = _js_dist if _component not in _chunk_map else _js_dist + _chunk_js_dist_map[_component]
    setattr(locals()[_component], '_js_dist', _component_js_dist)
    setattr(locals()[_component], '_css_dist', _css_dist)

# Update _js_dist to hold ALL chunks to ensure Dash can load them.
for _component in _chunk_js_dist_map:
    _js_dist += _chunk_js_dist_map[_component]
