# Changelog

All notable changes to this project will be documented in this file.

## [0.0.32] - UNRELEASED

### Changed

- Added support of kwargs (output, input, state) in callbacks [jfftonsic](https://github.com/thedirtyfew/dash-extensions/pull/15).
- The speed of Lottie animations can now be adjusted dynamically.

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
