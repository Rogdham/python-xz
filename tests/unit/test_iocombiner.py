from io import SEEK_SET, BytesIO
from typing import List, cast
from unittest.mock import Mock, call

import pytest

from xz.io import IOAbstract, IOCombiner, IOProxy


def generate_mock(length: int) -> Mock:
    mock = Mock()
    mock.__class__ = cast(Mock, IOAbstract)  # needs to be subclass of IOAbstract
    mock._length = length  # pylint: disable=protected-access
    mock.__len__ = lambda s: s._length  # pylint: disable=protected-access

    def write(data: bytes) -> int:
        mock._length += len(data)
        return len(data)

    mock.write.side_effect = write
    mock.writable.return_value = True
    return mock


#
# tell / seek
#


def test_seek() -> None:
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


#
# read
#


def test_read() -> None:
    originals: List[IOAbstract] = [
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
    assert not cast(Mock, originals[1]).method_calls


#
# write
#


def test_write() -> None:
    parts = []

    class Combiner(IOCombiner[IOAbstract]):
        def _create_fileobj(self) -> IOAbstract:
            fileobj = generate_mock(0)
            parts.append(fileobj)
            return fileobj

    with Combiner() as combiner:
        assert combiner.writable()
        assert len(parts) == 0

        # create new from scratch
        combiner.write(b"abc")
        assert len(parts) == 1
        assert parts[0].method_calls == [
            call.seek(0, SEEK_SET),
            call.write(memoryview(b"abc")),
        ]
        parts[0].method_calls.clear()

        combiner.write(b"def")
        assert len(parts) == 1
        assert parts[0].method_calls == [
            call.seek(3, SEEK_SET),
            call.writable(),
            call.write(memoryview(b"def")),
        ]
        parts[0].method_calls.clear()

        combiner.seek(8)
        combiner.write(b"ghi")
        assert len(parts) == 1
        assert parts[0].method_calls == [
            call.seek(6, SEEK_SET),
            call.writable(),
            call.write(memoryview(b"\x00\x00")),
            call.seek(8, SEEK_SET),
            call.writable(),
            call.write(memoryview(b"ghi")),
        ]
        parts[0].method_calls.clear()

        # not writable anymore -> create new fileobj
        parts[0].writable.return_value = False
        combiner.write(b"jkl")
        assert len(parts) == 2
        assert parts[0].method_calls == [
            call.seek(11, SEEK_SET),
            call.writable(),
            call.writable(),
        ]
        assert parts[1].method_calls == [
            call.seek(0, SEEK_SET),
            call.write(memoryview(b"jkl")),
        ]
        parts[0].method_calls.clear()
        parts[1].method_calls.clear()

        combiner.write(b"mno")
        assert len(parts) == 2
        assert not parts[0].method_calls
        assert parts[1].method_calls == [
            call.seek(3, SEEK_SET),
            call.writable(),
            call.write(memoryview(b"mno")),
        ]
        parts[1].method_calls.clear()

        # force change fileobj
        combiner._change_fileobj()  # pylint: disable=protected-access
        assert len(parts) == 3
        assert not parts[0].method_calls
        assert parts[1].method_calls == [
            call.writable(),
            call._write_end(),  # pylint: disable=protected-access
        ]
        assert not parts[2].method_calls
        parts[1].method_calls.clear()

        # force change fileobj again
        combiner._change_fileobj()  # pylint: disable=protected-access
        assert len(parts) == 4
        assert not parts[0].method_calls
        assert not parts[1].method_calls
        assert not parts[2].method_calls  # no call to _write_end
        assert not parts[3].method_calls
        parts[1].method_calls.clear()

        combiner.write(b"pqr")
        assert len(parts) == 4
        assert not parts[0].method_calls
        assert not parts[1].method_calls
        assert not parts[2].method_calls
        assert parts[3].method_calls == [
            call.seek(0, SEEK_SET),
            call.writable(),
            call.write(memoryview(b"pqr")),
        ]
        parts[3].method_calls.clear()

        # don't create fileobj if write nothing
        parts[1].writable.return_value = False
        combiner.write(b"")
        assert len(parts) == 4
        assert not parts[0].method_calls
        assert not parts[1].method_calls
        assert not parts[2].method_calls
        assert not parts[3].method_calls

    # check write_finish
    assert not parts[0].method_calls
    assert not parts[1].method_calls
    assert not parts[2].method_calls
    assert parts[3].method_calls == [
        call._write_end(),  # pylint: disable=protected-access
    ]

    # check if last fileobj is empty no calls to _write_end
    with Combiner() as combiner:
        combiner.write(b"abc")
        combiner._change_fileobj()  # pylint: disable=protected-access
        parts[0].method_calls.clear()
        assert not parts[1].method_calls
    assert not parts[0].method_calls
    assert not parts[1].method_calls  # no calls to _write_end


#
# truncate
#


def test_truncate() -> None:
    # pylint: disable=protected-access
    originals = [
        generate_mock(2),
        generate_mock(0),
        generate_mock(8),
        generate_mock(10),
        generate_mock(20),
    ]

    with IOCombiner(*originals) as combiner:

        # truncate between two boundaries
        combiner.truncate(17)
        assert originals[3].method_calls == [call.truncate(7)]
        assert not originals[4].method_calls
        assert dict(combiner._fileobjs) == {
            0: originals[0],
            2: originals[2],
            10: originals[3],
        }
        originals[3].reset_mock()

        # truncate after length
        combiner.truncate(42)
        assert originals[3].method_calls == [call.truncate(32)]
        assert dict(combiner._fileobjs) == {
            0: originals[0],
            2: originals[2],
            10: originals[3],
        }
        originals[3].reset_mock()

        # truncate at boundary
        combiner.truncate(10)
        assert dict(combiner._fileobjs) == {
            0: originals[0],
            2: originals[2],
        }
        assert not originals[2].method_calls
        assert not originals[3].method_calls

        # truncate at boundary
        combiner.truncate(2)
        assert dict(combiner._fileobjs) == {
            0: originals[0],
        }
        assert not originals[0].method_calls
        assert not originals[1].method_calls
        assert not originals[2].method_calls

        # truncate at start
        combiner.truncate(0)
        assert dict(combiner._fileobjs) == {}
        assert not originals[0].method_calls


#
# append
#


def test_append() -> None:
    combiner = IOCombiner[IOAbstract](generate_mock(13), generate_mock(37))
    assert len(combiner) == 50
    combiner._append(  # pylint: disable=protected-access
        IOProxy(BytesIO(b"abcdefghij"), 0, 10)
    )
    assert len(combiner) == 60
    combiner.seek(54)
    assert combiner.read(4) == b"efgh"


def test_append_invalid() -> None:
    combiner = IOCombiner[IOAbstract](generate_mock(13), generate_mock(37))
    assert len(combiner) == 50
    with pytest.raises(TypeError):
        # pylint: disable=protected-access
        combiner._append(BytesIO(b"abcdefghij"))  # type: ignore[arg-type]
