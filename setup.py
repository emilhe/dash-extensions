import json
import pathlib

from setuptools import setup

with open('package.json') as f:
    package = json.load(f)

package_name = package["name"].replace(" ", "_").replace("-", "_")

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name=package["name"],
    version=package["version"],
    author=package['author'],
    packages=[package_name],
    url="https://github.com/thedirtyfew/dash-extensions/",
    include_package_data=True,
    license=package['license'],
    long_description=README,
    long_description_content_type="text/markdown",
    description=package.get('description', package_name),
    install_requires=["dash", "more_itertools", "Flask-Caching", "jsbeautifier"],
    classifiers=[
        "Programming Language :: Python :: 3",
        'Framework :: Dash',
    ],
)
