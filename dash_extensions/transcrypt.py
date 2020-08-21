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


def transcrypt_module(module):
    dst_dir = "__target__"
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
    index_path = f"{dst_dir}/{index_file}"
    hash_path = f"{dst_dir}/{module_name}.md5"
    # Check if transcrypt if needed.
    if os.path.isfile(hash_path):
        with open(hash_path, 'r') as f:
            old_md5 = f.read()
        with open(module.__file__, 'rb') as f:
            new_md5 = hashlib.md5(f.read()).hexdigest()
        if old_md5 == new_md5:
            return index_path
    # Do the transcrypt.
    os.system("transcrypt -b {}".format(module.__file__))
    # Write index.
    with open(f"{dst_dir}/{index_file}", 'w') as f:
        f.write(Template(_main_template).substitute(funcs=",".join(funcs), namespace=module_name))
    # Write hash.
    with open(hash_path, 'w') as f:
        with open(module.__file__, 'rb') as inner:
            f.write(hashlib.md5(inner.read()).hexdigest())
    return index_path


def inject_js(dash_app, index_path):
    js_fn = os.path.basename(index_path)
    js_dir = os.path.dirname(index_path)

    @dash_app.server.route(f'/{js_dir}/<path:path>', methods=['GET'])
    def send_js(path):  # pragma: no cover
        return send_from_directory(js_dir, path)

    script_tag = f"<script type='module' src='/{js_dir}/{js_fn}'></script>\n            {{%scripts%}}"
    dash_app.index_string = dash_app.index_string.replace("{%scripts%}", script_tag)
