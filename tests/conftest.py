from itertools import chain, product
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Tuple

import pytest

if TYPE_CHECKING:
    from typing import List

    # see https://github.com/pytest-dev/pytest/issues/7469
    # for pytest exporting from pytest and not _pytest
    from _pytest.config import Config
    from _pytest.config.argparsing import Parser
    from _pytest.nodes import Item


def pytest_addoption(parser: "Parser") -> None:
    parser.addoption(
        "--generate-integration-files",
        action="store_true",
        default=False,
        help="Test the generation of the integration files",
    )


def pytest_collection_modifyitems(config: "Config", items: "List[Item]") -> None:
    root = Path(__file__).parent.parent
    for item in items:
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
