import hashlib
import os

from string import Template
from flask import send_from_directory

_main_template = """import {$funcs} from './$namespace.js'

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    $namespace: {
        $funcs
    }
});
"""


def bind(dash_app, module):
    index = _transcrypt_module(module)
    _serve_module(dash_app, index)


def _transcrypt_module(module):
    # Locate all functions.
    module_name, _ = os.path.splitext(os.path.basename(module.__file__))
    funcs = []
    for member in dir(module):
        if hasattr(getattr(module, member), "__call__"):
            funcs.append(member)
    # Decorate all module functions.
    for func in funcs:
        setattr(module, func, f"window.dash_clientside.{module_name}.{func}")
    # Setup index.
    index_file = f"{module_name}_index.js"
    hash_path = f"__target__/{module_name}.md5"
    # Check if transcrypt if needed.
    if os.path.isfile(hash_path):
        with open(hash_path, 'r') as inner:
            old_md5 = hashlib.md5(inner.read())
        with open(module.__file__, 'r') as inner:
            new_md5 = hashlib.md5(inner.read())
        if old_md5 == new_md5:
            return index_file
    # Do the transcrypt.
    os.system("transcrypt -b {}".format(module.__file__))
    # Write index.
    with open(f"__target__/{index_file}", 'w') as f:
        f.write(Template(_main_template).substitute(funcs=",".join(funcs), namespace=module_name))
    # Write hash.
    with open(hash_path, 'w') as f:
        with open(module.__file__, 'r') as inner:
            f.write(hashlib.md5(inner.read()))
    return index_file


def _serve_module(dash_app, index):
    @dash_app.server.route('/__target__/<path:path>', methods=['GET'])
    def send_js(path):  # pragma: no cover
        return send_from_directory('__target__', path)

    script_tag = f"<script type='module' src='/__target__/{index}'></script>\n            {{%scripts%}}"
    dash_app.index_string = dash_app.index_string.replace("{%scripts%}", script_tag)
