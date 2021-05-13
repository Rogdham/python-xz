from hashlib import sha1
import subprocess

import pytest


@pytest.mark.generate_integration_files
def test(integration_case, data_pattern):
    xz_path, metadata = integration_case

    expected_hash = sha1(xz_path.read_bytes())

    # note that we override current xz file
    # this allows to create new integration files from json metadata
    data = memoryview(data_pattern)
    with xz_path.open("wb") as fout:
        for step in metadata["generate"]:
            step_data_len = step.get("length", 0)
            step_data = data[:step_data_len]
            data = data[step_data_len:]
            fout.write(
                subprocess.run(
                    step["cmd"].split(" "),
                    input=step_data,
                    stdout=subprocess.PIPE,
                    check=True,
                ).stdout
            )
    assert not data

    generated_hash = sha1(xz_path.read_bytes())

    assert generated_hash.hexdigest() == expected_hash.hexdigest()
