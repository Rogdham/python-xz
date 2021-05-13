from io import BytesIO
from unittest.mock import Mock

import pytest

from xz.io import IOAbstract, IOCombiner, IOProxy


def generate_mock(length):
    mock = Mock()
    mock._length = length  # pylint: disable=protected-access
    mock.__class__ = IOAbstract
    return mock


def test_io_combiner_seek():
    originals = [
        generate_mock(2),
        generate_mock(0),
        generate_mock(8),
    ]
    combiner = IOCombiner(*originals)

    assert combiner.tell() == 0
    assert combiner.seek(7) == 7
    assert combiner.tell() == 7

    for original in originals:
        assert not original.method_calls  # did not touch original


def test_io_combiner_append():
    # pylint: disable=protected-access
    combiner = IOCombiner(generate_mock(13), generate_mock(37))
    assert combiner._length == 50
    combiner._append(IOProxy(BytesIO(b"abcdefghij"), 0, 10))
    assert combiner._length == 60
    combiner.seek(54)
    assert combiner.read(4) == b"efgh"


def test_io_combiner_append_invalid():
    # pylint: disable=protected-access
    combiner = IOCombiner(generate_mock(13), generate_mock(37))
    assert combiner._length == 50
    with pytest.raises(TypeError):
        combiner._append(BytesIO(b"abcdefghij"))


def test_io_combiner_read():
    originals = [
        IOProxy(BytesIO(b"abc"), 0, 3),
        generate_mock(0),  # size 0, will be never used
        IOProxy(BytesIO(b"defghij"), 0, 7),
    ]
    combiner = IOCombiner(*originals)

    # read all
    originals[0].seek(2)
    originals[2].seek(4)
    combiner.seek(0)
    assert combiner.read() == b"abcdefghij"
    assert originals[0].tell() == 3
    assert originals[2].tell() == 7
    combiner.seek(4)
    assert combiner.read() == b"efghij"
    assert originals[0].tell() == 3
    assert originals[2].tell() == 7

    # read partial
    originals[0].seek(2)
    originals[2].seek(4)
    combiner.seek(1)
    assert combiner.read(6) == b"bcdefg"
    assert originals[0].tell() == 3
    assert originals[2].tell() == 4
    assert combiner.read(6) == b"hij"
    assert originals[0].tell() == 3
    assert originals[2].tell() == 7
    assert combiner.read(6) == b""
    assert originals[0].tell() == 3
    assert originals[2].tell() == 7
    assert combiner.read(6) == b""
    assert originals[0].tell() == 3
    assert originals[2].tell() == 7

    # with original seek
    combiner.seek(1)
    originals[0].seek(2)
    originals[2].seek(4)
    assert combiner.read(5) == b"bcdef"
    assert originals[0].tell() == 3
    assert originals[2].tell() == 3

    # never used at all
    assert not originals[1].method_calls
