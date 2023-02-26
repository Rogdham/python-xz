from io import DEFAULT_BUFFER_SIZE
from lzma import compress
from pathlib import Path
from random import seed
import sys
from typing import BinaryIO, Optional, cast

import pytest

from xz import XZFile
from xz.common import create_xz_index_footer, parse_xz_footer, parse_xz_index
from xz.io import IOCombiner, IOStatic

if sys.version_info >= (3, 9):
    from collections.abc import Callable, Iterator
    from random import randbytes
else:
    from random import getrandbits
    from typing import Callable, Iterator

    def randbytes(length: int) -> bytes:
        return getrandbits(length * 8).to_bytes(length, "little")


@pytest.fixture
def ram_usage() -> Iterator[Callable[[], int]]:
    try:
        import tracemalloc  # pylint: disable=import-outside-toplevel
    except ImportError:  # e.g. PyPy
        pytest.skip("tracemalloc module not available")

    try:
        tracemalloc.start()
        yield lambda: tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


BLOCK_SIZE = 1_000_000


@pytest.fixture
def fileobj() -> BinaryIO:
    # create xz raw data composed of many identical blocks
    nb_blocks = 50

    seed(0)
    data = compress(randbytes(BLOCK_SIZE))
    header = data[:12]
    footer = data[-12:]
    check, backward_size = parse_xz_footer(footer)
    block = data[12 : -12 - backward_size]
    records = parse_xz_index(data[-12 - backward_size : -12])
    index_footer = create_xz_index_footer(check, records * nb_blocks)

    return cast(
        BinaryIO,
        IOCombiner(
            IOStatic(header),
            *[IOStatic(block)] * nb_blocks,
            IOStatic(index_footer),
        ),
    )


def test_read_linear(
    # pylint: disable=redefined-outer-name
    fileobj: BinaryIO,
    ram_usage: Callable[[], int],
) -> None:
    with XZFile(fileobj) as xz_file:
        # read almost one block
        xz_file.read(BLOCK_SIZE - 1)
        one_block_memory = ram_usage()

        # read all the file
        while xz_file.read(DEFAULT_BUFFER_SIZE):
            assert (
                # should not use much more memory, take 2 as error margin
                ram_usage()
                < one_block_memory * 2
            ), f"Consumes too much RAM (at {100 * xz_file.tell() / len(xz_file):.0f}%)"


def test_partial_read_each_block(
    # pylint: disable=redefined-outer-name
    fileobj: BinaryIO,
    ram_usage: Callable[[], int],
) -> None:
    one_block_memory: Optional[int] = None

    with XZFile(fileobj) as xz_file:
        for pos in xz_file.block_boundaries[1:]:
            # read second-to last byte of each block
            xz_file.seek(pos - 2)
            xz_file.read(1)
            if one_block_memory is None:
                one_block_memory = ram_usage()
            else:
                assert (
                    # default strategy is max 8 blocks, take 10 as error margin
                    ram_usage()
                    < one_block_memory * 10
                ), f"Consumes too much RAM (at {100 * xz_file.tell() / len(xz_file):.0f}%)"


def test_write(
    tmp_path: Path,
    # pylint: disable=redefined-outer-name
    ram_usage: Callable[[], int],
) -> None:
    nb_blocks = 10

    seed(0)

    one_block_memory: Optional[int] = None

    with XZFile(tmp_path / "archive.xz", "w") as xz_file:
        for i in range(nb_blocks):
            xz_file.change_block()
            xz_file.write(randbytes(BLOCK_SIZE))

            if one_block_memory is None:
                one_block_memory = ram_usage()
            else:
                assert (
                    # should not use much more memory, take 2 as error margin
                    ram_usage()
                    < one_block_memory * 2
                ), f"Consumes too much RAM (at {i / nb_blocks:.0f}%)"
