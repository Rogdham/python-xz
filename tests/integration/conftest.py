import json
from pathlib import Path

import pytest


@pytest.fixture(
    params=(Path(__file__).parent / "files").rglob("*.json"),
    ids=lambda path: path.name,
)
def integration_case(request):
    json_path = request.param
    with json_path.open() as json_file:
        metadata = json.load(json_file)
    return (json_path.with_suffix(".xz"), metadata)
