import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Tuple, cast

import pytest

if TYPE_CHECKING:

    class _Request(pytest.FixtureRequest):
        param: Path


_IntegrationCase = Tuple[Path, Dict[str, Any]]


@pytest.fixture(
    params=(Path(__file__).parent / "files").rglob("*.json"),
    ids=lambda path: cast(Path, path).name,
)
def integration_case(request: "_Request") -> _IntegrationCase:
    json_path = request.param
    with json_path.open() as json_file:
        metadata = cast(Dict[str, Any], json.load(json_file))
    return (json_path.with_suffix(".xz"), metadata)
