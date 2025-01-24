# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4] - 2025-01-24

### Added

- Fixed issue with unable to run sync in async context. Separated the sync and async prompt rendering into distinct classes.
- Added support for async prompt rendering
- Added tests for async prompt rendering
- Added tests for previous issues

## [0.1.2] - 2025-01-24

### Added

- Async support for prompt rendering
- Async tests for prompt rendering and full test coverage
- Fixed issue with dedent where the prompts render with extra unwanted spaces or tabs

## [0.1.0] - 2024-12-06

### Added

- Initial release
- Base prompt management system with type validation
- Jinja2 template integration
- Comprehensive test suite
- Support for system and user prompts
- Variable validation through Pydantic
- Custom configuration support
