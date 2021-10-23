from hashlib import sha256

import pytest

import xz


def test(integration_case, data_pattern, tmp_path):
    xz_path, metadata = integration_case
    data = memoryview(data_pattern)

    if "padding" in xz_path.name:
        pytest.skip("Write mode does not support stream padding yet")

    generated_path = tmp_path / "archive.xz"

    with xz.open(generated_path, "w") as xzfile:
        for stream in metadata["streams"]:
            xzfile.check = stream["check"]
            xzfile.change_stream()
            for block in stream["blocks"]:
                xzfile.filters = block.get("filters")
                xzfile.change_block()
                xzfile.write(data[: block["length"]])
                data = data[block["length"] :]

    assert not data

    expected_hash = sha256(xz_path.read_bytes())
    generated_hash = sha256(generated_path.read_bytes())

    assert generated_hash.hexdigest() == expected_hash.hexdigest()
