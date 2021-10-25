import os
import re
import json

from dash import Dash
from distutils.dir_util import copy_tree
from flask import request, jsonify, make_response

'''
This purpose of this module is to ease the integration of Dash with dataiku. 
'''


def parse_config(args):
    return {'webAppBackendUrl': args.get('webAppBackendUrl'), 'appPrefix': args.get('appPrefix')}


def get_dataiku_kwargs(server, config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        app_prefix = config['appPrefix']
        web_app_backend_url = config['webAppBackendUrl']
        return {
            'server': server,
            'routes_pathname_prefix': f'/{app_prefix}/',
            'requests_pathname_prefix': f"{web_app_backend_url}{app_prefix}/"
        }
    except FileNotFoundError:
        return {'server': server}


def setup_dataiku(server, config_path):
    # Add config route.
    @server.route("/configure")
    def configure():
        config = parse_config(request.args)
        # Check if the configuration has changed.
        if os.path.isfile(config_path):
            with open(config_path, 'r') as f:
                current_config = json.load(f)
            # Configuration has not changed, redirect to app.
            if config == current_config:
                return jsonify(success=True)
        # Configuration changed. Write new config and ask for restart.
        with open(config_path, 'w') as f:
            json.dump(config, f)
        return make_response(jsonify({'error': 'Configuration changed. Backend restart required.'}), 500)

    # Return keyword arguments.
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        app_prefix = config['appPrefix']
        web_app_backend_url = config['webAppBackendUrl']
        return {
            'server': server,
            'routes_pathname_prefix': f'/{app_prefix}/',
            'requests_pathname_prefix': f"{web_app_backend_url}{app_prefix}/"
        }
    except FileNotFoundError:
        return {'server': server}


def bind_assets_folder(app: Dash, app_id: str, assets_folder: str):
    # Create assets container folder for the app.
    dst_assets_folder = os.path.join(app.config.assets_folder, app_id)
    os.makedirs(dst_assets_folder, exist_ok=True)
    # Copy assets.
    copy_tree(assets_folder, dst_assets_folder)

    def _walk_assets_directory(self):
        walk_dir = os.path.join(self.config.assets_folder, app_id)  # EMHER: Use application sub dir
        slash_splitter = re.compile(r"[\\/]+")
        ignore_str = self.config.assets_ignore
        ignore_filter = re.compile(ignore_str) if ignore_str else None

        for current, _, files in sorted(os.walk(walk_dir)):
            if current == walk_dir:
                base = ""
            else:
                s = current.replace(walk_dir, "").lstrip("\\").lstrip("/")
                splitted = slash_splitter.split(s)
                if len(splitted) > 1:
                    base = "/".join(slash_splitter.split(s))
                else:
                    base = splitted[0]
            base = os.path.join(base, app_id)  # EMHER: Use application sub dir
            if ignore_filter:
                files_gen = (x for x in files if not ignore_filter.search(x))
            else:
                files_gen = files

            for f in sorted(files_gen):
                path = "/".join([base, f]) if base else f

                full = os.path.join(current, f)

                if f.endswith("js"):
                    self.scripts.append_script(self._add_assets_resource(path, full))
                elif f.endswith("css"):
                    self.css.append_css(self._add_assets_resource(path, full))
                elif f == "favicon.ico":
                    self._favicon = path

    app._walk_assets_directory = lambda x=app: _walk_assets_directory(app)
