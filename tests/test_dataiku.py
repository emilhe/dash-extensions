import os
from dash import Dash
from dash_extensions.dataiku import bind_assets_folder
from shutil import rmtree


def test_bind_assets_folder():
    app_id = "test_app"
    asset_name = "test.js"
    # Create a mock asset dir.
    tmp_dir = "/tmp/assets/"
    os.makedirs(tmp_dir, exist_ok=True)
    with open(os.path.join(tmp_dir, asset_name), 'w') as f:
        f.write("const a = 0;")
    # Clear the asset dir.
    app = Dash()
    dst_assets_folder = os.path.join(app.config.assets_folder, app_id)
    rmtree(dst_assets_folder)
    # Check that there are no assets.
    app._walk_assets_directory()
    resources = app.scripts._resources._resources
    assert len(resources) == 0
    # Bind the asset dir to the app.
    bind_assets_folder(app, "test_app", tmp_dir)
    # Check that asset(s) are now present.
    app._walk_assets_directory()
    resources = app.scripts._resources._resources
    assert resources[0]["asset_path"] == os.path.join(app_id, asset_name)
