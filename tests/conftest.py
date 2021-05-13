from itertools import chain, product
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--generate-integration-files",
        action="store_true",
        default=False,
        help="Test the generation of the integration files",
    )


def pytest_collection_modifyitems(config, items):
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
def data_pattern():
    return _DATA_PATTERN


@pytest.fixture(scope="session")
def data_pattern_locate():
    def locate(data):
        if len(data) < 3:
            raise ValueError("data to short")
        return (_DATA_PATTERN.index(data), len(data))

    yield locate
