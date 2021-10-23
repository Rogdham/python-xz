# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

[unreleased]: https://github.com/rogdham/bigxml/compare/v0.1.2...HEAD

### :rocket: Added

- Write modes (`w`, `x`, `r+`, `w+`, `x+`) :tada:
- Allow to `seek` past the end of the fileobj
- Calling `len` on a fileobj gives its length, and `bool` tells if it is empty
- Export useful constants and functions from `lzma` for easy access: checks, filters,
  etc.

### :house: Internal

- Test that no warnings are generated

## [0.1.2] - 2021-09-19

[0.1.2]: https://github.com/rogdham/python-xz/releases/tag/v0.1.2

### :rocket: Added

- Add `__version__` attribute to module, despite [PEP 396] being rejected

[pep 396]: https://www.python.org/dev/peps/pep-0396/

## [0.1.1] - 2021-05-14

[0.1.1]: https://github.com/rogdham/python-xz/releases/tag/v0.1.1

### :rocket: Added

- Implementation of the `fileno` method

## [0.1.0] - 2021-05-13

[0.1.0]: https://github.com/rogdham/python-xz/releases/tag/v0.1.0

### :rocket: Added

- Initial public release :tada:
