from io import UnsupportedOperation

import pytest

from xz.io import IOAbstract


def test_io_abstract_attributes():
    obj = IOAbstract(10)
    assert obj.readable() is True
    assert obj.seekable() is True
    assert obj.writable() is False


def test_io_abstract_tell_seek():
    obj = IOAbstract(10)
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


def test_io_abstract_tell_read():
    class Impl(IOAbstract):
        def __init__(self):
            super().__init__(10)

        def _read(self, size):
            # for tests, does not rely on position
            return b"xyz"[:size]

    obj = Impl()

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


def test_io_abstract_tell_read_empty():
    class Impl(IOAbstract):
        def __init__(self):
            super().__init__(10)
            self.empty_reads = 100

        def _read(self, size):
            self.empty_reads -= 1
            if self.empty_reads > 0:
                return b""
            return b"a"

    obj = Impl()

    assert obj.read() == b"aaaaaaaaaa"


def test_io_abstract_fileno(tmp_path):
    file_path = tmp_path / "file"
    file_path.write_bytes(b"abcd")

    class Impl(IOAbstract):
        # pylint: disable=abstract-method

        def __init__(self, fileobj):
            super().__init__(10)
            self.fileobj = fileobj

    with file_path.open("rb") as fin:
        obj = Impl(fin)
        assert obj.fileno() == fin.fileno()


def test_io_abstract_fileno_ko():
    obj = IOAbstract(10)
    with pytest.raises(UnsupportedOperation):
        obj.fileno()
