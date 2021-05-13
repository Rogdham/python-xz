from io import BytesIO
from unittest.mock import Mock

from xz.io import IOProxy


def test_io_proxy_seek():
    original = Mock()
    proxy = IOProxy(original, 4, 14)

    assert proxy.tell() == 0
    assert proxy.seek(7) == 7
    assert proxy.tell() == 7

    assert not original.method_calls  # did not touch original


def test_io_proxy_read():
    original = BytesIO(b"xxxxabcdefghijyyyyy")
    proxy = IOProxy(original, 4, 14)

    # read all
    original.seek(2)
    proxy.seek(0)
    assert proxy.read() == b"abcdefghij"
    assert original.tell() == 14
    proxy.seek(4)
    assert proxy.read() == b"efghij"
    assert original.tell() == 14

    # read partial
    original.seek(2)
    proxy.seek(6)
    assert proxy.read(3) == b"ghi"
    assert original.tell() == 13
    assert proxy.read(3) == b"j"
    assert original.tell() == 14
    assert proxy.read(3) == b""
    assert original.tell() == 14
    assert proxy.read(3) == b""
    assert original.tell() == 14

    # with original seek
    original.seek(2)
    proxy.seek(4)
    original.seek(1)
    assert proxy.read() == b"efghij"
    assert original.tell() == 14
