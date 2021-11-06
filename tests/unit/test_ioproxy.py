from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, call

from xz.io import IOProxy


def test_fileno(tmp_path: Path) -> None:
    file_path = tmp_path / "file"
    file_path.write_bytes(b"abcd")

    with file_path.open("rb") as fin:
        obj = IOProxy(fin, 1, 3)
        assert obj.fileno() == fin.fileno()


def test_seek() -> None:
    original = Mock()
    proxy = IOProxy(original, 4, 14)

    assert proxy.tell() == 0
    assert proxy.seek(7) == 7
    assert proxy.tell() == 7

    assert not original.method_calls  # did not touch original


def test_read() -> None:
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


def test_write() -> None:
    original = BytesIO(b"xxxxabcdefghijyyyyy")
    with IOProxy(original, 4, 14) as proxy:
        proxy.seek(10)

        assert proxy.write(b"uvw") == 3
        assert original.getvalue() == b"xxxxabcdefghijuvwyy"

        assert proxy.write(b"UVWXYZ") == 6
        assert original.getvalue() == b"xxxxabcdefghijuvwUVWXYZ"


def test_truncate() -> None:
    original = Mock()
    with IOProxy(original, 4, 14) as proxy:
        assert proxy.truncate(5) == 5
        assert original.method_calls == [call.truncate(9)]
        original.reset_mock()

        assert proxy.truncate(20) == 20
        assert original.method_calls == [call.truncate(24)]
