import os
import re
from distutils.dir_util import copy_tree

from dash import Dash

"""
The purpose of this module is to ease the integration of Dash with Dataiku.
"""


def bind_assets_folder(app: Dash, app_id: str, assets_folder: str):  # noqa: C901
    """
    Dataiku 10 doesn't support separate asset folders for each Dash app. This function targets fixing this issue by
    (1) creating a new asset sub folder for each app, and (2) limiting asset loading to this folder.
    """
    # Create assets container folder for the app.
    dst_assets_folder = os.path.join(app.config.assets_folder, app_id)
    os.makedirs(dst_assets_folder, exist_ok=True)
    # Copy assets.
    copy_tree(assets_folder, dst_assets_folder)

    def _walk_assets_directory(self):
        walk_dir = os.path.join(
            self.config.assets_folder, app_id
        )  # EMHER: Use application sub dir
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
