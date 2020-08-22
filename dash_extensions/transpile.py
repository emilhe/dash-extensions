import hashlib
import os
import subprocess

from string import Template
from dash.dependencies import ClientsideFunction
from flask import send_from_directory

_main_template = """import {$funcs} from './$module.js'

window.$namespace = Object.assign({}, window.$namespace, {
    $module: {
        $funcs
    }
});
"""


def module_to_clientside_functions(module):
    return module_to_javascript(module, namespace="dash_clientside", func_mapper=_clientside_function_mapper)


def _clientside_function_mapper(x, y, z):
    return ClientsideFunction(y, z)


def module_to_props(module, namespace="dash_props"):
    return module_to_javascript(module, namespace=namespace, func_mapper=_prop_mapper)


def _prop_mapper(x, y, z):
    return f"window.{x}.{y}.{z}"


def module_to_javascript(module, namespace, func_mapper=None):
    dst_dir = "__target__"
    # Locate all functions.
    module_name, _ = os.path.splitext(os.path.basename(module.__file__))
    funcs = []
    for member in dir(module):
        if hasattr(getattr(module, member), "__call__"):
            funcs.append(member)
    # Decorate all module functions.
    if func_mapper is not None:
        for func in funcs:
            setattr(module, func, func_mapper(namespace, module_name, func))
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
    # Do the transcrypt. TODO: Check output?
    output = subprocess.check_output(['transcrypt', '-b', module.__file__])
    # Write index.
    with open(f"{dst_dir}/{index_file}", 'w') as f:
        f.write(Template(_main_template).substitute(funcs=",".join(funcs), module=module_name, namespace=namespace))
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
        return send_from_directory(os.path.join(os.getcwd(), js_dir), path)

    script_tag = f"<script type='module' src='/{js_dir}/{js_fn}'></script>\n            {{%scripts%}}"
    dash_app.index_string = dash_app.index_string.replace("{%scripts%}", script_tag)
