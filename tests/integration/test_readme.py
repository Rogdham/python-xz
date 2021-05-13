import doctest
import os
from pathlib import Path

import pytest

import xz


@pytest.fixture(autouse=True, scope="module")
def change_dir():
    old_dir = os.getcwd()
    os.chdir(Path(__file__).parent / "files")
    yield
    os.chdir(old_dir)


def _parse_readme():
    code_blocks = []
    current_code_block = ""
    current_code_block_line = None
    with (Path(__file__).parent.parent.parent / "README.md").open() as fin:
        for line_no, line in enumerate(fin):
            if line.startswith("```"):
                if current_code_block_line is None:
                    if "python" in line:
                        current_code_block_line = line_no + 1
                else:
                    code_blocks.append((current_code_block_line, current_code_block))
                    current_code_block = ""
                    current_code_block_line = None
            elif current_code_block_line is not None:
                current_code_block += line
    return code_blocks


_README_CODE_BLOCKS = _parse_readme()


@pytest.fixture(
    params=[
        pytest.param(code_block, id=f"line_{line_no}")
        for line_no, code_block in _README_CODE_BLOCKS
    ]
)
def readme_block_path(request, tmp_path):
    path = tmp_path / "block.txt"
    path.write_text(request.param)
    yield path
    path.unlink()


def test_readme(readme_block_path):  # pylint: disable=redefined-outer-name
    failure_count, test_count = doctest.testfile(
        readme_block_path,
        module_relative=False,
        extraglobs={"xz": xz},
    )
    assert failure_count == 0
    assert test_count
