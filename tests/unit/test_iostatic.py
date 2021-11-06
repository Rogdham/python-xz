from io import UnsupportedOperation

import pytest

from xz.io import IOStatic


def test_read() -> None:
    static = IOStatic(b"abcdefghij")

    # read all
    static.seek(0)
    assert static.read() == b"abcdefghij"
    static.seek(4)
    assert static.read() == b"efghij"

    # read partial
    static.seek(6)
    assert static.read(3) == b"ghi"
    assert static.read(3) == b"j"
    assert static.read(3) == b""
    assert static.read(3) == b""


def test_write() -> None:
    with IOStatic(b"abc") as static:
        assert static.writable() is False
        static.seek(3)
        with pytest.raises(UnsupportedOperation):
            static.write(b"def")


def test_truncate() -> None:
    with IOStatic(b"abc") as static:
        assert static.writable() is False
        with pytest.raises(UnsupportedOperation):
            static.truncate()
