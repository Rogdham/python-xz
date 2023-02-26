from itertools import chain, product
from pathlib import Path
import sys
from typing import List, Tuple

import pytest

if sys.version_info >= (3, 9):  # pragma: no cover
    from collections.abc import Callable, Iterator
else:  # pragma: no cover
    from typing import Callable, Iterator


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--generate-integration-files",
        action="store_true",
        default=False,
        help="Test the generation of the integration files",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: List[pytest.Item]
) -> None:
    root = Path(__file__).parent.parent
    for item in items:
        if item.fspath:
            relative = Path(item.fspath).parent.relative_to(root)
            mark = relative.name
            item.add_marker(getattr(pytest.mark, mark))
    if not config.getoption("--generate-integration-files"):
        skip_mark = pytest.mark.skip(
            reason="need --generate-integration-files option to run"
        )
        for item in items:
            if "generate_integration_files" in item.keywords:
                item.add_marker(skip_mark)


# any 3 consecutive bytes is unique in _DATA_PATTERN
_DATA_PATTERN = bytes(
    chain(
        *product(
            range(65, 91),  # uppercase
            range(97, 123),  # lowercase
            range(48, 58),  # digit
        )
    )
)


@pytest.fixture(scope="session")
def data_pattern() -> bytes:
    return _DATA_PATTERN


@pytest.fixture(scope="session")
def data_pattern_locate() -> Iterator[Callable[[bytes], Tuple[int, int]]]:
    def locate(data: bytes) -> Tuple[int, int]:
        if len(data) < 3:
            raise ValueError("data to short")
        return (_DATA_PATTERN.index(data), len(data))

    yield locate
