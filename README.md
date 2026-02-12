[![PyPI Latest Release](https://img.shields.io/pypi/v/dash-extensions.svg)](https://pypi.org/project/dash-extensions/)
[![codecov](https://img.shields.io/codecov/c/github/thedirtyfew/dash-extensions?logo=codecov)](https://codecov.io/gh/thedirtyfew/dash-extensions)
[![Testing](https://github.com/thedirtyfew/dash-extensions/actions/workflows/python-test.yml/badge.svg)](https://github.com/thedirtyfew/dash-extensions/actions/workflows/python-test.yml)
[![CodeQL](https://github.com/thedirtyfew/dash-extensions/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/thedirtyfew/dash-extensions/actions/workflows/codeql-analysis.yml)

The `dash-extensions` package is a collection of utility functions, syntax extensions, and Dash components that aim to improve the Dash development experience. Here is a brief overview,

-   The `enrich` module, which contains various enriched versions of Dash components
-   A number of custom components, e.g. the `Websocket` component, which enables real-time communication and push notifications
-   The `javascript` module, which contains functionality to ease the interplay between Dash and JavaScript
-   The `logging` module, which makes it a breeze to route logs to your Dash UI
-   The `events` module, which facilitates event flows in Dash
-   The `pages` module, which extends the functionality of [Dash Pages](https://dash.plotly.com/urls)
-   The `snippets/utils/validation/streaming` modules, which contain a collection of utility functions (documentation limited to source code comments)

The `enrich` module enables a number of _transforms_ that add functionality and/or syntactic sugar to Dash. Examples include

-   Making it possible to avoid invoking a callback _if it is already running_ via the `BlockingCallbackTransform`
-   Improving app performance via the `ServersideOutputTransform`
-   Automated serialization/deserialization of [Pydantic](https://docs.pydantic.dev/latest/) models via the `BaseModelTransform`

to name a few. To enable interactivity, the documentation has been moved to a [separate page](http://dash-extensions.com).

NB: The 2.0.0 version introduces a number of breaking changes, see documentation for details.

## Release flow

Release metadata is managed with `scripts/release.py`:

-   `npm run release:prepare -- --version X.Y.Z` updates `package.json`, syncs `pyproject.toml`, and creates a changelog template section if missing.
-   `npm run release:verify -- --version X.Y.Z` validates versions and changelog content before tagging.
-   `npm run release:notes -- --version X.Y.Z` prints the matching changelog section.

When a tag like `2.0.6` is pushed, the `Create GitHub Release From Tag` workflow creates the GitHub release message from `CHANGELOG.md`. The publish workflow then runs on the release event.

## Donation

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=Z9RXT5HVPK3B8&currency_code=DKK&source=url)
