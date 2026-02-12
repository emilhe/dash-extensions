# Changelog

All notable changes to this project will be documented in this file.

## [2.0.5] - 12-02-26

### Changed

-   Various Dash 3/4 compatibility fixes
-   Fixed bug with Wildcard import [#400](https://github.com/emilhe/dash-extensions/issues/400). Contributed by [Aaron-Wrote-This](https://github.com/Aaron-Wrote-This)

## [2.0.4] - 22-04-25

### Changed

-   Fixed bug with background callback registration [#312](https://github.com/emilhe/dash-extensions/issues/312). Contributed by [MartinSA04](https://github.com/MartinSA04)

## [2.0.3] - 10-04-25

### Changed

-   Relax Python version constraint
-   Fixed bug in `Loading` component build process

## [2.0.1] - 02-04-25

### Changed

-   A few improvements in the `events` module
-   Added support for optional types in serialization transforms, thereby fixing [#345](https://github.com/emilhe/dash-extensions/issues/345)

## [2.0.0] - 02-04-25

### Added

-   Added new `logging` module as a replacement for the (removed) LogTransform

### Changed

-   All components rewritten in TypeScript
-   Refactor all but the tiniest component to be async, thereby reducing (main) bundle size to 11.7 kB
-   Update to React 18, update dependencies accordingly fixing various security bugs
-   Change the `Lottie` component to be based on `lottie-react` instead of `react-lottie` (not maintained) [BREAKING CHANGE]
-   Update the `Mermaid` component to the most recent version, thereby fixing [#362](https://github.com/emilhe/dash-extensions/issues/362)
-   Change build/dependency management system to uv
-   Update Dash dependency to 3.0.0 [BREAKING CHANGE], thereby fixing [#378](https://github.com/emilhe/dash-extensions/issues/280).
-   Fixed bug in SSE component (only observed in Dash 3)
-   Fixed bug in `fix_page_load_anchor_issue` function

### Removed

-   Dropped `dataiku` module (targeted old Dataiku vesion, not maintained for years) [BREAKING CHANGE]
-   Dropped `NoOutputTransform` as the functionality (no output) has been available in "pure" Dash since 2.17.0 [BREAKING CHANGE]
-   Dropped `LogTransform`. New Dash functionality allows a leaner implementation, now found in the `logging` module [BREAKING CHANGE]

## [1.0.20] - 02-01-25

### Added

-   Added support for changing the `url` property of the `Websocket` component. Contributed by [lgln-kmi](https://github.com/lgln-kmi)
-   Added new `timeout` property to the `Websocket` component to control how long to wait for the websocket to (re)connect
-   Added `events` module
-   Added `id` property to `DeferScript` component. Contributed by [escobar-felipe](https://github.com/escobar-felipe)

### Changed

-   Improved stability of `EventListener` for dynamic use cases

## [1.0.19] - 26-11-24

### Changed

-   Updated various dependencies. Added support for / change target Python version to 3.13

## [1.0.18] - 15-07-24

### Changed

-   Fix bug in `BlockingCallbackTransform` which occurred when a multi-output was targeted (i.e. using the `ALL` wildcard)

## [1.0.17] - 28-06-24

### Added

-   Improve the stability of the serialization transforms (`BaseModelTransform`, and `DataclassTransform`) by adding support for `None`, `str` and `dict` types
-   Add the option to send objects to the `captureKeys` property of the `Keyboard` component to enable more specific filtering
-   Add streaming capabilities to the `SSE` component

## [1.0.16] - 05-28-24

### Added

-   Add new `SSE` component, which can receive (and buffer) server sent events such the output from an LLM.
-   Add new `LoadingTransform`, which makes it easy to re-use a single (full screen) loading component across the app.
-   Add new `BaseModelTransform`, which automates serialization/deserialization of Pydantic `BaseModel` objects.

## [1.0.15] - 05-04-24

### Added

-   Add new `Loading` component, which makes it possible to block events (e.g. keyboard input) while a component is loading.
-   Add support for client side callbacks in the `TriggerTransform`. Contributed by [lcornelatti](https://github.com/andressommerhoff).

### Changed

-   Updated dependencies, including `dash` to `2.17.0`, and `dash-mantine-components` (optional) to `0.14.3`. The latter includes breaking changes, e.g. the renaming of `NotificationsProvider` to `NotificationProvider`

## [1.0.14] - 05-03-24

### Added

-   Add new `validate` module, which adds an `assert_no_random_ids` that assets that Dash didn't generate any random component ids.

## [1.0.13] - 05-03-24

### Added

-   Add new `pages` module, which introduces the `page components` and `page properties` concepts.

## [1.0.12] - 04-02-23

### Changed

-   Set `allow_duplicate=True` for the default logging configurations for the `LogTransform`, thereby fixing [#280](https://github.com/emilhe/dash-extensions/issues/280).

## [1.0.11] - 03-02-23

### Changed

-   Add `useCapture` property to `EventListener` and `Keyboard` components, thereby fixing [#255](https://github.com/emilhe/dash-extensions/issues/255).

## [1.0.10] - 03-02-23

### Changed

-   Update dependencies, including `Flask-caching`, thereby fixing [#296](https://github.com/emilhe/dash-extensions/issues/296).

## [1.0.9] - 03-02-23

### Changed

-   Fixed bug in `Keyboard` component where the keydown event would fire twice.

## [1.0.8] - 25-01-23

### Changed

-   Fixed bug in `BlockingCallbackTransform` component where the callback would never get invoked again, if an (uncaught) exception was raised during execution. Contributed by [lcornelatti](https://github.com/lcornelatti).

## [1.0.7] - 27-12-23

### Added

-   Re-introduce `Keyboard` component (due to many user requests)

## [1.0.4] - 07-10-23

### Added

-   Publishing to npm added to CICD pipeline. Fixes [#284](https://github.com/emilhe/dash-extensions/issues/284)

### Changed

-   Dependencies updated
-   Dynamic prefixing is now applied recursively
-   Inline JS functions created using `assign` are now re-used if the code is identical

## [1.0.3] - 31-07-23

### Added

-   Added `SerializationTransform` and `DataclassTransform`

### Changed

-   Dependencies updated

### Removed

-   The `Ticker` component has been removed. With the underlying component no longer being maintained, its dependency version requirement had fallen behind

## [1.0.1] - 22-05-23

### Changed

-   Fix of bug that caused `ServersideOutputTransform` not to be applied when return type was `tuple`

## [1.0.0] - 12-05-23

### Removed

-   The `OperatorTransform` has been removed, as [similar functionality](https://dash.plotly.com/partial-properties) has been implemented in the core Dash library as part of the Dash 2.9 release

### Changed

-   The syntax of the `ServersideOutputTransform` has been changed. Instead of using `ServersideOutput` in place of the `Output`, one must now wrap return values in `Serverside` objects
-   The `MultiplexerTransform` has been changed to simply set a flag to enable multiplexing, which has been included as part of the Dash 2.9 release (with the default being disabled)
-   Add support for embedding of blueprints in function layouts
-   Add `DashBlueprint` support for args/kwargs. Fixes [#250](https://github.com/thedirtyfew/dash-extensions/issues/250)
-   Remove `WebSocket` event handlers prior to close. Fixes [#160](https://github.com/thedirtyfew/dash-extensions/issues/160)

## [0.1.13] - 28-02-23

### Changed

-   Add support for embedding of blueprints in function layouts

## [0.1.12] - 23-02-23

### Changed

-   Mitigation of #241 attempted. Race condition hard to reproduce, validity of fix is uncertain
-   Addressed bugs #245 + #242
-   Fixed bug #243
-   Bump dependencies

## [0.1.11] - 23-01-23

### Changed

-   Fixed bug in html table generator

## [0.1.10] - 04-01-23

### Changed

-   Performance improvement of `BlockingCallbackTransform`

## [0.1.9] - 03-01-23

### Changed

-   Bump a number of npm packages to address security issues
-   Bump `dash-mantine-components` to 0.11.0, and update code accordingly (to mitigate introduced breaking changes)

## [0.1.8] - 05-12-22

### Changed

-   Bump a number of npm packages to address security issues
-   Change callback context of `BlockingCallbackTransform` callbacks to reflect the original trigger
-   Add `priority` keyword argument for callbacks that makes it possible to select which callbacks take precedence, when multiple callbacks target the same output simultaneously using the `MultiplexerTransform`
-   Add support for the unittest syntax [introduced with Dash 2.6](https://dash.plotly.com/testing)

## [0.1.7] - 08-11-22

### Changed

-   Bump dependencies to `dash>=2.7.0` (including a compatibility fix) and `Flask-Caching==2.0.1`

## [0.1.6] - 10-09-22

### Changed

-   Reimplementation of the `BeforeAfter` component by @AnnMarieW adding new features and improved mobile compatibility. NB: This is a **breaking** change, please consult the docs for an example using the new syntax
-   Improved support for the new `callback(background=True, ...)` syntax adding support for the `set_progress` keyword
-   Added syntax sugar for Celery task registration for use with the `CeleryManager` object
-   Added explicit raise of `NotImplementedError` for the (deprecated) `long_callback` syntax

## [0.1.5] - 17-07-22

### Added

-   Added `OperatorTransform` and the associated `Operator` class

### Changed

-   Fixed bug in `MultiPlexerTransform` occurring when used together with `PrefixIdTransform`
-   Fixed bug [#178](https://github.com/thedirtyfew/dash-extensions/issues/178) occurring when using `ServersideOutput` as `State`
-   Bump `Dash` to version >=2.5.0, and added pages import in `enrich` module

## [0.1.4] - 11-07-22

### Changed

-   Drop spurious `Burger` references as reported in [#188](https://github.com/thedirtyfew/dash-extensions/issues/188)
-   Update to `flask-caching==2.0.0`, with the `FileSystemStore` code changed accordingly. Should fix [#181](https://github.com/thedirtyfew/dash-extensions/issues/181)
-   Add extra attribute check to address issue in [#185](https://github.com/thedirtyfew/dash-extensions/issues/185)
-   Updated various dependencies

## [0.1.3] - 13-05-22

### Added

-   Added support for flexible callback signatures

### Changed

-   Added info on pypi (has been missing after poetry migration)
-   Added `CycleBreakerInput` component, which is to be used instead of the `break_cycle` keyword in 0.1.1
-   Fixed introduced bug when mixing imports from `dash` and `dash_extensions.enrich`

## [0.1.1] - 10-05-22

### Added

-   Added `CycleBreaker` component, strategy contributed by @TomaszRewak
-   Added `CycleBreakerTransform` transform

### Changed

-   Add [location path name in `WebSocket` component default url](https://github.com/thedirtyfew/dash-extensions/pull/91) by @0x0ACB
-   Improve `BlockingCallbackTransform` adding a [final callback invocation blocking ends](https://github.com/thedirtyfew/dash-extensions/pull/169) by @TomaszRewak
-   Bug when a single output of list type was used with `LogTransform` and `BlockingCallbackTransform` fixed by @TomaszRewak
-   Bug where an attempt was made to write to read-only properties in `hijack` utility function fixed by @RafaelWO
-   Remap of callback bindings in `DashProxy` post init to enable callback registration via the `before_first_request` hook (need for compatibility with the latest `pages` implementation)
-   Updated various dependencies to address security vulnerabilities

## [0.1.0] - 21-04-22

### Added

-   Added tests for the main parts of the code
-   Added LGTM analysis for the main parts of the code
-   Added a new, interactive documentation page

### Changed

-   Most of the `dataiku` module has been dropped. The dropped parts were only relevant for old Dataiku versions
-   The `enrich` module has been refactored, with the `DashBluePrint` and `CallbackBlueprint` being introduced as part of the refactor
-   Added `escape` functionality to `PrefixIdTransform`, default to escape ids starting with "a-" (used for anchors)
-   A few changes/update to the `fix_page_load_anchor_issue` function

### Removed

-   The `multipage` module. Please use the `pages` plugin instead (available in [dash-labs](https://github.com/plotly/dash-labs))
-   The `websockets` module. Please refer to the new, interactive documentation for updated examples
-   The `examples` package. Please refer to the new, interactive documentation for updated examples
-   The `Burger` component. Please look at `dash-mantine-components` for an alternative
-   The `Download` component. It was migrated to `dash-core-components` a some time ago, but has been kept around for backwards compatibility
-   The `Keyboard` component. The `EventListener` component can do the same, but is more general
-   The `Monitor` component. Now that Dash has introduced (limited) support for circular callbacks, it has become irrelevant
-   Most of the readme. Please refer to the new, interactive documentation for updated examples

## [0.0.71] - 18-02-22

### Change

-   Some stability improvements of `LogTransform`.

## [0.0.70] - 16-02-22

### Added

-   Added `LogTransform`, which enables the callback `log` keyword.

## [0.0.69] - 05-02-22

### Added

-   Added `BlockingCallbackTransform`, which enables the callback `blocking` keyword.

## [0.0.68] - 03-02-22

### Added

-   Added `DashEventSource` component.

## [0.0.67] - 18-12-21

### Added

-   Added `EventListener` component.

## [0.0.66] - 13-12-21

### Change

-   Added support in the `enrich` module for Dash 2.0 style callbacks that don't use the app object.

## [0.0.65] - 08-11-21

### Change

-   Changed loading of js chunks so that a chunk is only loaded when actually needed.

## [0.0.63] - 06-11-21

### Change

-   Added all `dash` elements to `enrich` module (e.g. `html` and `dcc`) to enable drop-in replacement.

## [0.0.61] - 05-11-21

### Change

-   Added `jsbeautifier` package as install dependency.
-   Updates code and example to Dash 2.0 syntax.

## [0.0.60] - 09-08-21

### Added

-   Added `Purify` component to enable rendering of (sanitized) html.

### Change

-   The `Mermaid` components now supports dynamic rendering (the component was rewritten completely from scratch).
-   Changed `Mermaid`, `Lottie`, and `Burger` components to use async loading. As a result, the size of the main `dash-extensions` bundle was reduced from > 1 MB to < 50 kB (!).

## [0.0.58] - 30-06-21

### Added

-   Added `Mermaid` component.
-   Added `DeferScript` component.

## [0.0.57] - 21-06-21

### Change

-   Fixed `State` missing in `enrich` import.

## [0.0.56] - 19-06-21

### Added

-   Added `arg_check` keyword argument to `ServersideOutput` and `ServersideOutputTransform` components. If set to false, the function arguments are not considered when updating the cache.

### Change

-   Bugfix in `assign` functionality when multiple functions are assigned.
-   Bugfix in `NoOutputTransform` addressing an [issue](https://github.com/thedirtyfew/dash-extensions/issues/79) seen with multiple workers.

## [0.0.55] - 22-05-21

### Added

-   A new `assign` function to the `javascript` module to enable writing inline JavaScript functions.

### Change

-   Relaxed `WebSocket` proptype validation.

## [0.0.53] - 24-04-21

### Added

-   Support for Redis in `ServersideOutputTransform` via a new `RedisStore` component (experimental).
-   New `keyup`, `n_keyups`, and `keys_pressed` props to `Keyboard` component.
-   Support for the `ALL` wildcard in `MultiplexerTransform`, and MATCH/ALLSMALLER now raises an appropriate error.
-   New proxy_wrapper feature (useful for e.g. the `Loading` component) in `MultiplexerTransform`.
-   Support for client side callback transforms in `DashProxy`.
-   Client side callback support in `MultiplexerTransform`, `PrefixIdTransform`, and `NoOutputTransform`.
-   Automated modification of the `target` property of the `Tooltip` component in `PrefixIdTransform`.

## [0.0.51] - 07-04-21

### Change

-   Bugfix in `MultiplexerTransform` when `proxy_location='inplace'`.

## [0.0.49] - 02-04-21

### Change

-   Bugfix in `ServersideOutput` when using `dash.no_update`.

## [0.0.48] - 02-04-21

### Change

-   Bugfixes in `MultiplexerTransform`, both of dcc.Loading and of proxies firing unintentionally on load.
-   Reintroduced the `TriggerTransform` based on community feedback.
-   Security fixes of underlying npm packages.

## [0.0.47] - 21-03-21

### Added

-   A new `MultiplexerTransform` that makes it possible to target an output multiple times.
-   A new `BeforeAfter` component to show before/after images.

### Change

-   Updated `Burger` component; added new properties, added new example, slight changes to interface.
-   Updated `multipage_app.py` example; removed dependency on burger menu, removed burger helper function in `multipage.py`.
-   Added a `hijack` function to the `DashProxy` object. It can be used to inject app state into other app objects, typically used in frameworks such as dataiku 9.0 where the `Dash` object is constructed outside of the user code context.

### Remove

-   Removed the `GroupTransform` (not really necessary with the new `MultiplexerTransform`).
-   Removed the `TriggerTransform`.

## [0.0.46] - 11-03-21

### Change

-   Added a new function in the `dataiku` module.

## [0.0.45] - 06-02-21

### Change

-   Added support for dict IDs in the `Monitor` component thanks to [Yook74](https://github.com/thedirtyfew/dash-extensions/issues/45).

## [0.0.44] - 12-01-21

### Added

-   Added `dataiku` module (to ease integration of Dash apps in [dataiku](https://www.dataiku.com/)).

## [0.0.42] - 09-01-21

### Changes

-   Bugfix in `Burger` thanks to [JonThom](https://github.com/thedirtyfew/dash-extensions/issues/39).

## [0.0.41] - 03-01-21

### Changes

-   Bugfix in `NoOutputTransform`.

## [0.0.40] - 31-12-20

### Changes

-   Renaming of `websocket.py` to `websockets.py` to address a [Windows compatibility issue](https://github.com/thedirtyfew/dash-extensions/issues/38).

## [0.0.39] - 28-12-20

### Added

-   Added `WebSocket` component and `websocket.py` file with websocket utils.
-   Added `Ticker` component.

## [0.0.38] - 16-12-20

### Changed

-   Bug fix related to [callback grouping with multiple inputs](https://github.com/thedirtyfew/dash-extensions/issues/34).

## [0.0.37] - 14-12-20

### Added

-   Added `Burger` component and `multipage` module.

### Changed

-   Change name of `DashTransformer` to `DashProxy`.
-   Added support for mixing of dash.depencency components (i.e. Input, Output, ...) and enriched components.

## [0.0.33] - 30-11-20

### Added

-   Added wild card support for the `group` keyword, requested by [gedemagt](https://github.com/thedirtyfew/dash-extensions/issues/27)

## [0.0.32] - 27-11-20

### Added

-   A new `javascript` module has been added. It holds helper functions/classes related to the python/javascript interface.
-   Added support for kwargs (output, input, state) in callbacks [jfftonsic](https://github.com/thedirtyfew/dash-extensions/pull/15).
-   Added `Monitor` component. Intended use cases include bi-directional component property synchronization.

### Changed

-   The speed of Lottie animations can now be adjusted dynamically.
-   Memoize keyword can now be a function. If it is, the data is transformed by the function before memoization.

## [0.0.31] - 23-08-20

### Removed

-   The module for transpiling Python code to javascript has been moved to a separate package, dash-transcrypt.

## [0.0.30] - 23-08-20

### Added

-   A new module for transpiling Python code to javascript.
-   A new n_keydowns props to the Keyboard component to make it possible to capture all keyboard events.

## [0.0.28] - 2020-12-08

### Changed

-   A few bug fixes.

## [0.0.26] - 2020-31-07

### Added

-   A new `enrich` module has been added. It exposes the functionality of previous callback blueprints (and more!) through a drop in replacement of (enriched) Dash components.
-   Added folder of example code.

### Changed

-   Major refactoring of callback functionality. It has now been moved to the new `enrich` module.

## [0.0.24] - 2020-27-07

### Added

-   Keyboard component.

## [0.0.21] - 2020-23-07

### Changed

-   PropType validation for Download component fixed.

### Added

-   CallbackCache class.
