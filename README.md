[![PyPI Latest Release](https://img.shields.io/pypi/v/dash-extensions.svg)](https://pypi.org/project/dash-extensions/)
[![codecov](https://img.shields.io/codecov/c/github/thedirtyfew/dash-extensions?logo=codecov)](https://codecov.io/gh/thedirtyfew/dash-extensions)
[![Testing](https://github.com/thedirtyfew/dash-extensions/actions/workflows/python-test.yml/badge.svg)](https://github.com/thedirtyfew/dash-extensions/actions/workflows/python-test.yml)
[![CodeQL](https://github.com/thedirtyfew/dash-extensions/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/thedirtyfew/dash-extensions/actions/workflows/codeql-analysis.yml)

The `dash-extensions` package is a collection of utility functions, syntax extensions, and Dash components that aim to improve the Dash development experience. It can be divided in four main pillars,

* The `enrich` module, which contains various enriched versions of Dash components
* A number of custom components, e.g. the `Websocket` component, which enables real-time communication and push notifications
* The `javascript` module, which contains functionality to ease the interplay between Dash and JavaScript
* The `snippets` module, which contains a collection of utility functions (documentation limited to source code comments)

The `enrich` module enables a number of _transforms_ that add functionality and/or syntactic sugar to Dash. Examples include

* Making it possible to avoid invoking a callback _if it is already running_ via the `BlockingCallbackTransform`
* Enabling logging from within Dash callbacks via the `LogTransform`
* Improving app performance via the `ServersideOutputTransform`

to name a few. To enable interactivity, the documentation has been moved to a [separate page](http://dash-extensions.com).

NB: The 1.0.0 version introduces a number of breaking changes, see documentation for details.

## Donation

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=Z9RXT5HVPK3B8&currency_code=DKK&source=url)
