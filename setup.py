import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="dash-extensions",
    version="0.0.5",
    description="Various extensions for the Plotly Dash framework",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/thedirtyfew/dash-extensions/",
    author="Emil Haldrup Eriksen",
    author_email="emil.h.eriksen@gmail.com",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    packages=["dash_extensions"],
    include_package_data=True,
    install_requires=["dash", "more_itertools"],
)
