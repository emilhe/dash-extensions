[![PyPI Latest Release](https://img.shields.io/pypi/v/dash-extensions.svg)](https://pypi.org/project/dash-extensions/)
[![codecov](https://img.shields.io/codecov/c/github/thedirtyfew/dash-extensions?logo=codecov)](https://codecov.io/gh/thedirtyfew/dash-extensions)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/thedirtyfew/dash-extensions.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/thedirtyfew/dash-extensions/context:python)
[![Language grade: JavaScript](https://img.shields.io/lgtm/grade/javascript/g/thedirtyfew/dash-extensions.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/thedirtyfew/dash-extensions/context:javascript)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?)](http://makeapullrequest.com)
[![Testing](https://github.com/thedirtyfew/dash-extensions/actions/workflows/python-test.yml/badge.svg)](https://github.com/thedirtyfew/dash-extensions/actions/workflows/python-test.yml)

The `dash-extensions` package is a collection of utility functions, syntax extensions, and Dash components that aim to improve the Dash development experience. It can be divided in four main pillars,

* The `enrich` module, which contains various enriched versions of Dash components
* A number of custom components, e.g. the `Websocket` component, which enables real-time communication
* The `javascript` module, which contains functionality to ease the interplay between Dash and JavaScript
* The `snippets` module, which contains a collection of utility functions (documentation limited to source code comments)

The `enrich` module enables a number of _transforms_ that add functionality and/or syntactic sugar to Dash. Examples include

* Making it possible to target an `Output` by multiple callbacks via the `MultiplexerTransform`
* Enabling logging from within Dash callbacks via the `LogTransform`
* Improving app performance via the `ServersideOutputTransform`

to name a few. To enable interactivity, the documentation has been moved a [separate page](http://dash-extensions.onrender.com).

NB: The 0.1.0 version introduces a number of breaking changes, see the changelog for details.
