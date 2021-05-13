from xz.io import IOStatic


def test_io_proxy_read():
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
