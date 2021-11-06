from io import DEFAULT_BUFFER_SIZE, UnsupportedOperation
from pathlib import Path
from typing import IO
from unittest.mock import Mock, call

import pytest

from xz.io import IOAbstract

#
# len
#


def test_len() -> None:
    obj = IOAbstract(10)
    assert len(obj) == 10


#
# fileno
#


def test_fileno(tmp_path: Path) -> None:
    file_path = tmp_path / "file"
    file_path.write_bytes(b"abcd")

    class Impl(IOAbstract):
        def __init__(self, fileobj: IO[bytes]) -> None:
            super().__init__(10)
            self.fileobj = fileobj

    with file_path.open("rb") as fin:
        obj = Impl(fin)
        assert obj.fileno() == fin.fileno()


def test_fileno_ko() -> None:
    obj = IOAbstract(10)
    with pytest.raises(UnsupportedOperation):
        obj.fileno()


#
# tell / seek
#


def test_seek_not_seekable() -> None:
    class Impl(IOAbstract):
        def __init__(self) -> None:
            super().__init__(10)

        def seekable(self) -> bool:
            return False

    obj = Impl()
    assert obj.seekable() is False
    with pytest.raises(UnsupportedOperation) as exc_info:
        obj.seek(1)
    assert str(exc_info.value) == "seek"


def test_tell_seek() -> None:
    obj = IOAbstract(10)
    assert obj.seekable() is True
    assert obj.tell() == 0

    # absolute (no whence)
    assert obj.seek(1) == 1
    assert obj.tell() == 1
    assert obj.seek(3) == 3
    assert obj.tell() == 3
    assert obj.seek(10) == 10
    assert obj.tell() == 10
    with pytest.raises(ValueError) as exc_info:
        obj.seek(-1)
    assert str(exc_info.value) == "invalid seek position"
    assert obj.seek(42) == 42
    assert obj.tell() == 42

    # absolute (with whence)
    assert obj.seek(5, 0) == 5
    assert obj.tell() == 5
    assert obj.seek(10, 0) == 10
    assert obj.tell() == 10
    with pytest.raises(ValueError) as exc_info:
        obj.seek(-1, 0)
    assert str(exc_info.value) == "invalid seek position"
    assert obj.seek(42, 0) == 42
    assert obj.tell() == 42

    # relative
    assert obj.seek(10) == 10
    assert obj.seek(-7, 1) == 3
    assert obj.tell() == 3
    assert obj.seek(2, 1) == 5
    assert obj.tell() == 5
    with pytest.raises(ValueError) as exc_info:
        obj.seek(-6, 1)
    assert str(exc_info.value) == "invalid seek position"
    assert obj.tell() == 5
    assert obj.seek(37, 1) == 42
    assert obj.tell() == 42

    # from end
    assert obj.seek(0, 2) == 10
    assert obj.tell() == 10
    assert obj.seek(-4, 2) == 6
    assert obj.tell() == 6
    assert obj.seek(-10, 2) == 0
    assert obj.tell() == 0
    assert obj.seek(32, 2) == 42
    assert obj.tell() == 42
    with pytest.raises(ValueError) as exc_info:
        obj.seek(-11, 2)
    assert str(exc_info.value) == "invalid seek position"

    # from error
    with pytest.raises(ValueError) as exc_info:
        obj.seek(42, 3)
    assert str(exc_info.value) == "unsupported whence value"

    # seek after close
    obj.close()
    with pytest.raises(ValueError) as exc_info:
        obj.seek(0)
    assert str(exc_info.value) == "I/O operation on closed file"


#
# read
#


def test_read_non_readable() -> None:
    class Impl(IOAbstract):
        def __init__(self) -> None:
            super().__init__(10)

        def readable(self) -> bool:
            return False

    obj = Impl()
    assert obj.readable() is False
    with pytest.raises(UnsupportedOperation) as exc_info:
        obj.read(1)
    assert str(exc_info.value) == "read"


def test_tell_read() -> None:
    class Impl(IOAbstract):
        def __init__(self) -> None:
            super().__init__(10)

        def _read(self, size: int) -> bytes:
            # for tests, does not rely on position
            return b"xyz"[:size]

        def _write_after(self) -> None:
            raise RuntimeError("should not be called")

    obj = Impl()
    assert obj.tell() == 0

    # read all
    assert obj.read() == b"xyzxyzxyzx"
    obj.seek(5)
    assert obj.read() == b"xyzxy"

    # read from pos
    obj.seek(3)
    assert obj.read(2) == b"xy"
    assert obj.read(2) == b"xy"
    assert obj.read(2) == b"xy"
    assert obj.read(2) == b"x"
    assert obj.read(2) == b""
    assert obj.read(2) == b""

    # read from after EOF
    obj.seek(11)
    assert obj.read(2) == b""

    # read after close
    obj.close()
    with pytest.raises(ValueError) as exc_info:
        obj.read(1)
    assert str(exc_info.value) == "I/O operation on closed file"


def test_tell_read_empty() -> None:
    class Impl(IOAbstract):
        def __init__(self) -> None:
            super().__init__(10)
            self.empty_reads = 100

        def _read(self, size: int) -> bytes:
            self.empty_reads -= 1
            if self.empty_reads > 0:
                return b""
            return b"a"

    obj = Impl()
    assert obj.tell() == 0
    assert obj.read() == b"aaaaaaaaaa"


#
# write
#


def test_write_non_writeable() -> None:
    class Impl(IOAbstract):
        def __init__(self) -> None:
            super().__init__(10)

        def writable(self) -> bool:
            return False

    with Impl() as obj:
        assert obj.writable() is False
        with pytest.raises(UnsupportedOperation) as exc_info:
            obj.write(b"hello")
        assert str(exc_info.value) == "write"


@pytest.mark.parametrize("write_partial", (True, False))
def test_write_full(write_partial: bool) -> None:
    class Impl(IOAbstract):
        def __init__(self) -> None:
            super().__init__(10)
            self.mock = Mock()

        def _write_before(self) -> None:
            self.mock.write_start()

        def _write_after(self) -> None:
            self.mock.write_finish()

        def _write(self, data: bytes) -> int:
            self.mock.write(bytes(data))
            if write_partial:
                return min(2, len(data))
            return len(data)

    with Impl() as obj:

        # write before end
        obj.seek(5)
        with pytest.raises(ValueError) as exc_info:
            obj.write(b"abcdef")
        assert str(exc_info.value) == "write is only supported from EOF"
        assert not obj.mock.called

        # write at end
        obj.seek(10)
        assert obj.write(b"") == 0
        assert obj.tell() == 10
        assert not obj.mock.called
        assert obj.write(b"ghijkl") == 6
        assert obj.tell() == 16
        if write_partial:
            assert obj.mock.method_calls == [
                call.write_start(),
                call.write(b"ghijkl"),
                call.write(b"ijkl"),
                call.write(b"kl"),
            ]
        else:
            assert obj.mock.method_calls == [
                call.write_start(),
                call.write(b"ghijkl"),
            ]
        obj.mock.reset_mock()

        # write after end
        obj.seek(20)
        assert obj.write(b"mnopq") == 5
        assert obj.tell() == 25
        if write_partial:
            assert obj.mock.method_calls == [
                call.write(b"\x00\x00\x00\x00"),
                call.write(b"\x00\x00"),
                call.write(b"mnopq"),
                call.write(b"opq"),
                call.write(b"q"),
            ]
        else:
            assert obj.mock.method_calls == [
                call.write(b"\x00\x00\x00\x00"),
                call.write(b"mnopq"),
            ]
        obj.mock.reset_mock()

        # (big) write nothing after end (used e.g. by tuncate)
        limit = 30 if write_partial else int(DEFAULT_BUFFER_SIZE * 3.7)
        obj.seek(limit)
        assert obj.write(b"") == 0
        assert obj.tell() == limit
        if write_partial:
            assert obj.mock.method_calls == [
                call.write(b"\x00\x00\x00\x00\x00"),
                call.write(b"\x00\x00\x00"),
                call.write(b"\x00"),
            ]
        else:
            assert obj.mock.method_calls == [
                call.write(b"\x00" * DEFAULT_BUFFER_SIZE),
                call.write(b"\x00" * DEFAULT_BUFFER_SIZE),
                call.write(b"\x00" * DEFAULT_BUFFER_SIZE),
                call.write(b"\x00" * (limit - 3 * DEFAULT_BUFFER_SIZE - 25)),
            ]
        obj.mock.reset_mock()

        # close calls write_finish once
        obj.close()
        assert obj.mock.method_calls == [call.write_finish()]
        obj.mock.reset_mock()
        obj.close()
        assert not obj.mock.method_calls
        obj.close()

        # write after close
        with pytest.raises(ValueError) as exc_info:
            obj.write(b"xyz")
        assert str(exc_info.value) == "I/O operation on closed file"


#
# truncate
#


def test_truncate_non_writeable() -> None:
    class Impl(IOAbstract):
        def __init__(self) -> None:
            super().__init__(10)

        def writable(self) -> bool:
            return False

    with Impl() as obj:
        assert obj.writable() is False
        with pytest.raises(UnsupportedOperation) as exc_info:
            obj.truncate(4)
        assert str(exc_info.value) == "truncate"


@pytest.mark.parametrize("with_size", (True, False))
def test_truncate_with_size(with_size: bool) -> None:
    class Impl(IOAbstract):
        def __init__(self) -> None:
            super().__init__(10)
            self.mock = Mock()

        def _write_before(self) -> None:
            self.mock.write_start()

        def _write_after(self) -> None:
            self.mock.write_finish()

        def _write(self, data: bytes) -> int:
            raise RuntimeError("should not be called")

        def _truncate(self, size: int) -> None:
            self.mock.truncate(size)

    with Impl() as obj:
        obj.seek(7)
        assert not obj.mock.method_calls

        def truncate(size: int) -> int:
            if with_size:
                return obj.truncate(size)
            obj.seek(size)
            return obj.truncate()

        # truncate before start
        with pytest.raises(ValueError) as exc_info:
            obj.truncate(-1)
        assert str(exc_info.value) == "invalid truncate size"
        assert not obj.mock.method_calls

        # truncate before end
        assert truncate(5) == 5
        assert not with_size or obj.tell() == 7
        assert len(obj) == 5
        assert obj.mock.method_calls == [call.write_start(), call.truncate(5)]
        obj.mock.reset_mock()

        # truncate at end
        assert truncate(5) == 5
        assert not with_size or obj.tell() == 7
        assert len(obj) == 5
        assert not obj.mock.method_calls
        obj.mock.reset_mock()

        # truncate after end
        assert truncate(20) == 20
        assert not with_size or obj.tell() == 7
        assert len(obj) == 20
        assert obj.mock.method_calls == [call.truncate(20)]
        obj.mock.reset_mock()

        # close calls write_finish once
        obj.close()
        assert obj.mock.method_calls == [call.write_finish()]
        obj.mock.reset_mock()
        obj.close()
        assert not obj.mock.method_calls

        # truncate after close
        with pytest.raises(ValueError) as exc_info:
            obj.truncate(5)
        assert str(exc_info.value) == "I/O operation on closed file"
