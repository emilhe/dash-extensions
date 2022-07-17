# Changelog

All notable changes to this project will be documented in this file.

## [0.1.5] - 17-07-22

### Added

- Added `OperatorTransform` and the associated `Operator` class

### Changed

- Fixed bug in `MultiPlexerTransform` occurring when used together with `PrefixIdTransform`
- Fixed bug [#178](https://github.com/thedirtyfew/dash-extensions/issues/178) occurring when using `ServersideOutput` as `State`
- Bump `Dash` to version >=2.5.0, and added pages import in `enrich` module

## [0.1.4] - 11-07-22

### Changed

- Drop spurious `Burger` references as reported in [#188](https://github.com/thedirtyfew/dash-extensions/issues/188)
- Update to `flask-caching==2.0.0`, with the `FileSystemStore` code changed accordingly. Should fix [#181](https://github.com/thedirtyfew/dash-extensions/issues/181)
- Add extra attribute check to address issue in [#185](https://github.com/thedirtyfew/dash-extensions/issues/185)
- Updated various dependencies

## [0.1.3] - 13-05-22

### Added

- Added support for flexible callback signatures

### Changed

- Added info on pypi (has been missing after poetry migration) 
- Added `CycleBreakerInput` component, which is to be used instead of the `break_cycle` keyword in 0.1.1
- Fixed introduced bug when mixing imports from `dash` and `dash_extensions.enrich`

## [0.1.1] - 10-05-22

### Added

- Added `CycleBreaker` component, strategy contributed by @TomaszRewak
- Added `CycleBreakerTransform` transform

### Changed

- Add [location path name in `WebSocket` component default url](https://github.com/thedirtyfew/dash-extensions/pull/91) by @0x0ACB
- Improve `BlockingCallbackTransform` adding a [final callback invocation blocking ends](https://github.com/thedirtyfew/dash-extensions/pull/169) by @TomaszRewak
- Bug when a single output of list type was used with `LogTransform` and `BlockingCallbackTransform` fixed by @TomaszRewak
- Bug where an attempt was made to write to read-only properties in `hijack` utility function fixed by @RafaelWO
- Remap of callback bindings in `DashProxy` post init to enable callback registration via the `before_first_request` hook (need for compatibility with the latest `pages` implementation)
- Updated various dependencies to address security vulnerabilities

## [0.1.0] - 21-04-22

### Added

- Added tests for the main parts of the code
- Added LGTM analysis for the main parts of the code
- Added a new, interactive documentation page

### Changed

- Most of the `dataiku` module has been dropped. The dropped parts were only relevant for old Dataiku versions
- The `enrich` module has been refactored, with the `DashBluePrint` and `CallbackBlueprint` being introduced as part of the refactor
- Added `escape` functionality to `PrefixIdTransform`, default to escape ids starting with "a-" (used for anchors)
- A few changes/update to the `fix_page_load_anchor_issue` function

### Removed

- The `multipage` module. Please use the `pages` plugin instead (available in [dash-labs](https://github.com/plotly/dash-labs))
- The `websockets` module. Please refer to the new, interactive documentation for updated examples
- The `examples` package. Please refer to the new, interactive documentation for updated examples
- The `Burger` component. Please look at `dash-mantine-components` for an alternative
- The `Download` component. It was migrated to `dash-core-components` a some time ago, but has been kept around for backwards compatibility
- The `Keyboard` component. The `EventListener` component can do the same, but is more general
- The `Monitor` component. Now that Dash has introduced (limited) support for circular callbacks, it has become irrelevant
- Most of the readme. Please refer to the new, interactive documentation for updated examples

## [0.0.71] - 18-02-22

### Change

- Some stability improvements of `LogTransform`.

## [0.0.70] - 16-02-22

### Added

- Added `LogTransform`, which enables the callback `log` keyword.

## [0.0.69] - 05-02-22

### Added

- Added `BlockingCallbackTransform`, which enables the callback `blocking` keyword.

## [0.0.68] - 03-02-22

### Added

- Added `DashEventSource` component.

## [0.0.67] - 18-12-21

### Added

- Added `EventListener` component.

## [0.0.66] - 13-12-21

### Change

- Added support in the `enrich` module for Dash 2.0 style callbacks that don't use the app object.

## [0.0.65] - 08-11-21

### Change

- Changed loading of js chunks so that a chunk is only loaded when actually needed.

## [0.0.63] - 06-11-21

### Change

- Added all `dash` elements to `enrich` module (e.g. `html` and `dcc`) to enable drop-in replacement.

## [0.0.61] - 05-11-21

### Change

- Added `jsbeautifier` package as install dependency.
- Updates code and example to Dash 2.0 syntax.

## [0.0.60] - 09-08-21

### Added

- Added `Purify` component to enable rendering of (sanitized) html.

### Change

- The `Mermaid` components now supports dynamic rendering (the component was rewritten completely from scratch).
- Changed `Mermaid`, `Lottie`, and `Burger` components to use async loading. As a result, the size of the main `dash-extensions` bundle was reduced from > 1 MB to < 50 kB (!).

## [0.0.58] - 30-06-21

### Added

- Added `Mermaid` component.
- Added `DeferScript` component.

## [0.0.57] - 21-06-21

### Change

- Fixed `State` missing in `enrich` import.

## [0.0.56] - 19-06-21

### Added

- Added `arg_check` keyword argument to `ServersideOutput` and `ServersideOutputTransform` components. If set to false, the function arguments are not considered when updating the cache.

### Change

- Bugfix in `assign` functionality when multiple functions are assigned.
- Bugfix in `NoOutputTransform` addressing an [issue](https://github.com/thedirtyfew/dash-extensions/issues/79) seen with multiple workers.

## [0.0.55] - 22-05-21

### Added

- A new `assign` function to the `javascript` module to enable writing inline JavaScript functions.

### Change

- Relaxed `WebSocket` proptype validation.

## [0.0.53] - 24-04-21

### Added

- Support for Redis in `ServersideOutputTransform` via a new `RedisStore` component (experimental).
- New  `keyup`, `n_keyups`, and `keys_pressed` props to `Keyboard` component.
- Support for the `ALL` wildcard in `MultiplexerTransform`, and MATCH/ALLSMALLER now raises an appropriate error.
- New proxy_wrapper feature (useful for e.g. the `Loading` component) in `MultiplexerTransform`.
- Support for client side callback transforms in `DashProxy`.
- Client side callback support in `MultiplexerTransform`, `PrefixIdTransform`, and `NoOutputTransform`.
- Automated modification of the `target` property of the `Tooltip` component in `PrefixIdTransform`.

## [0.0.51] - 07-04-21

### Change

- Bugfix in `MultiplexerTransform` when `proxy_location='inplace'`.

## [0.0.49] - 02-04-21

### Change

- Bugfix in `ServersideOutput` when using `dash.no_update`.

## [0.0.48] - 02-04-21

### Change

- Bugfixes in `MultiplexerTransform`, both of dcc.Loading and of proxies firing unintentionally on load. 
- Reintroduced the `TriggerTransform` based on community feedback.
- Security fixes of underlying npm packages.

## [0.0.47] - 21-03-21

### Added

- A new `MultiplexerTransform` that makes it possible to target an output multiple times.
- A new `BeforeAfter` component to show before/after images.

### Change

- Updated `Burger` component; added new properties, added new example, slight changes to interface.
- Updated `multipage_app.py` example; removed dependency on burger menu, removed burger helper function in `multipage.py`.
- Added a `hijack` function to the `DashProxy` object. It can be used to inject app state into other app objects, typically used in frameworks such as dataiku 9.0 where the `Dash` object is constructed outside of the user code context. 

### Remove

- Removed the `GroupTransform` (not really necessary with the new `MultiplexerTransform`).
- Removed the `TriggerTransform`.

## [0.0.46] - 11-03-21

### Change

- Added a new function in the `dataiku` module.

## [0.0.45] - 06-02-21

### Change

- Added support for dict IDs in the `Monitor` component thanks to [Yook74](https://github.com/thedirtyfew/dash-extensions/issues/45).

## [0.0.44] - 12-01-21

### Added

- Added `dataiku` module (to ease integration of Dash apps in [dataiku](https://www.dataiku.com/)).

## [0.0.42] - 09-01-21

### Changes

- Bugfix in `Burger` thanks to [JonThom](https://github.com/thedirtyfew/dash-extensions/issues/39).

## [0.0.41] - 03-01-21

### Changes

- Bugfix in `NoOutputTransform`.

## [0.0.40] - 31-12-20

### Changes

- Renaming of `websocket.py` to `websockets.py` to address a [Windows compatibility issue](https://github.com/thedirtyfew/dash-extensions/issues/38).

## [0.0.39] - 28-12-20

### Added

- Added `WebSocket` component and `websocket.py` file with websocket utils.
- Added `Ticker` component.

## [0.0.38] - 16-12-20

### Changed

- Bug fix related to [callback grouping with multiple inputs](https://github.com/thedirtyfew/dash-extensions/issues/34).

## [0.0.37] - 14-12-20

### Added

- Added `Burger` component and `multipage` module.

### Changed

- Change name of `DashTransformer` to `DashProxy`.
- Added support for mixing of dash.depencency components (i.e. Input, Output, ...) and enriched components.

## [0.0.33] - 30-11-20

### Added

- Added wild card support for the `group` keyword, requested by [gedemagt](https://github.com/thedirtyfew/dash-extensions/issues/27)

## [0.0.32] - 27-11-20

### Added

- A new `javascript` module has been added. It holds helper functions/classes related to the python/javascript interface.
- Added support for kwargs (output, input, state) in callbacks [jfftonsic](https://github.com/thedirtyfew/dash-extensions/pull/15).
- Added `Monitor` component. Intended use cases include bi-directional component property synchronization.

### Changed

- The speed of Lottie animations can now be adjusted dynamically.
- Memoize keyword can now be a function. If it is, the data is transformed by the function before memoization.

## [0.0.31] - 23-08-20

### Removed

- The module for transpiling Python code to javascript has been moved to a separate package, dash-transcrypt.

## [0.0.30] - 23-08-20

### Added

- A new module for transpiling Python code to javascript.
- A new n_keydowns props to the Keyboard component to make it possible to capture all keyboard events.

## [0.0.28] - 2020-12-08

### Changed

- A few bug fixes.

## [0.0.26] - 2020-31-07

### Added

- A new `enrich` module has been added. It exposes the functionality of previous callback blueprints (and more!) through a drop in replacement of (enriched) Dash components. 
- Added folder of example code.

### Changed

- Major refactoring of callback functionality. It has now been moved to the new `enrich` module.

## [0.0.24] - 2020-27-07

### Added

- Keyboard component.

## [0.0.21] - 2020-23-07

### Changed

- PropType validation for Download component fixed.

### Added

- CallbackCache class.
