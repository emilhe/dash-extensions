# Changelog

All notable changes to this project will be documented in this file.

## [0.0.47] - UNRELEASED

### Added

- A new `MultiplexerTransform` that makes it possible to target an output multiple times.
- A new `BeforeAfter` component (to show before/after images).

### Change

- Updated `Burger` component; added new properties, added new example, slight changes to interface.
- Updated `multipage_app.py` example; removed dependency on burger menu, removed burger helper function in `multipage.py`.
- Added a `hijack` function to the `DashProxy` object. It can be used to inject app state into other app objects, typically used in frameworks such as dataiku where the `Dash` object is constructed outside of the user code context. 

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
