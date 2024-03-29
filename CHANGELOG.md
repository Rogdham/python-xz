# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [0.5.0] - 2023-02-27

[0.5.0]: https://github.com/rogdham/python-xz/releases/tag/v0.5.0

### :boom: Breaking changes

- End of Python 3.6 support

### :house: Internal

- Necessary code changes following dev dependency update: black, pylint, pytest
- Refactor a descriptor following PEP 487
- Add tests for CPython 3.11 and PyPy 3.9
- Use CPython 3.11 for misc. tests
- Update Github actions dependencies
- Import typing modules impacted by PEP 585 based on Python version

## [0.4.0] - 2022-01-09

[0.4.0]: https://github.com/rogdham/python-xz/releases/tag/v0.4.0

### :rocket: Added

- Advanced users may use the new `block_read_strategy` argument of `XZFile`/`xz.open` to
  customize the strategy for freeing block readers, and implement a different tradeoff
  between memory consumption and read speed when alternating reads between several
  blocks; the following strategies are provided: `RollingBlockReadStrategy` and
  `KeepBlockReadStrategy`

### :bug: Fixes

- Free memory after a block is fully read
- Free memory of LZMA decompressors when many blocks are partially read; this is a
  tradeoff defaulting to keeping the last 8 LZMA decompressors used
- Typing: use `BinaryIO` instead of `IO[bytes]`

### :house: Internal

- Specify the Python versions required in package metadata
- Test the `mode` attribute of objects returned by `xz.open`/`XZFile`
- Minor improvements in some docstrings

## [0.3.1] - 2021-12-26

[0.3.1]: https://github.com/rogdham/python-xz/releases/tag/v0.3.1

### :house: Internal

- Add tests for CPython 3.10 and PyPy 3.8
- Use CPython 3.10 for misc. tests
- Clarify which Python versions are supported in readme
- Fix some linting issues found by latest versions of mypy/pylint

## [0.3.0] - 2021-11-07

[0.3.0]: https://github.com/rogdham/python-xz/releases/tag/v0.3.0

### :boom: Breaking changes

- The `filename` argument of `XZFile` is now mandatory; this change should have very
  limited impact as not providing it makes no sense and would have raised a `TypeError`,
  plus it was already mandatory on `xz.open`

### :rocket: Added

- Type hints

### :house: Internal

- Type validation with mypy
- Distribute `py.typed` file in conformance with [PEP 561]

[pep 561]: https://www.python.org/dev/peps/pep-0561/

## [0.2.0] - 2021-10-23

[0.2.0]: https://github.com/rogdham/python-xz/releases/tag/v0.2.0

### :rocket: Added

- Write modes (`w`, `x`, `r+`, `w+`, `x+`) :tada:
- Allow to `seek` past the end of the fileobj
- Calling `len` on a fileobj gives its length, and `bool` tells if it is empty
- Export useful constants and functions from `lzma` for easy access: checks, filters,
  etc.

### :house: Internal

- Test that no warnings are generated
- Change development status to Alpha

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
