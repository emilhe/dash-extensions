import json

import tomli
import tomli_w

# Read version from package.json
with open("package.json", "r") as f:
    package = json.load(f)
version = package["version"]
description = package["description"]

# Load pyproject.toml
pyproject_path = "pyproject.toml"
with open(pyproject_path, "r") as f:
    pyproject = tomli.loads(f.read())

# Assume your project configuration is under the [project] table
pyproject.setdefault("project", {})["version"] = version
pyproject.setdefault("project", {})["description"] = description

# Write back the updated version
with open(pyproject_path, "wb") as f:
    tomli_w.dump(pyproject, f)

print(f"Updated pyproject.toml to version {version}")
