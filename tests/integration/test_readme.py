import doctest
import os
from pathlib import Path
import shutil
from typing import Iterator, List, Optional, Tuple

import pytest

import xz


@pytest.fixture(autouse=True)
def change_dir(tmp_path: Path) -> Iterator[None]:
    old_dir = os.getcwd()
    shutil.copy(Path(__file__).parent / "files" / "example.xz", tmp_path)
    os.chdir(tmp_path)
    yield
    os.chdir(old_dir)


def _parse_readme() -> List[Tuple[int, str]]:
    code_blocks = []
    current_code_block = ""
    current_code_block_line: Optional[int] = None
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


@pytest.mark.parametrize(
    "code_block",
    [
        pytest.param(code_block, id=f"line_{line_no}")
        for line_no, code_block in _README_CODE_BLOCKS
    ],
)
def test_readme(
    code_block: str, tmp_path: Path
) -> None:  # pylint: disable=redefined-outer-name
    path = tmp_path / "block.txt"
    path.write_text(code_block)
    failure_count, test_count = doctest.testfile(
        str(path),
        module_relative=False,
        extraglobs={"xz": xz},
    )
    assert failure_count == 0
    assert test_count
