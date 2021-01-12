import os
import json
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
