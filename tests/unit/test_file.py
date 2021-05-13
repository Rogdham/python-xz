from io import BytesIO
import os

import pytest

from xz.common import XZError
from xz.file import XZFile

FILE_BYTES = bytes.fromhex(
    # stream 1: two blocks (lengths: 100, 90)
    "fd377a585a0000016922de360200210116000000742fe5a3e0006300415d0020"
    "9842100431d01ab2853283057ddb5924a128599cc9911a7fcff8d59c1f6f887b"
    "cee97b1f83f1808f005de273e1a6e99a7eac4f8f632b7e43bbf1da311dce5c00"
    "00000000e7c35efa0200210116000000742fe5a3e00059003d5d00320cc42641"
    "c8b91ac7908be7e635b8e7d681d74b683cde914399f8de5460dc672363f1e067"
    "5a3ebac9f427ecbebcb94552c0dba85b26950f0ac98b22390000000031f4ee87"
    "00025964555a0000041276283e300d8b020000000001595a"
    # stream padding
    "0000000000000000000000000000000000000000000000000000000000000000"
    "000000000000000000000000000000000000000000000000"
    # stream 2: 4 blocks (lengths: 60, 60, 60, 30)
    "fd377a585a000004e6d6b4460200210116000000742fe5a3e0003b002d5d0033"
    "8cc42671c8b91ac7908be7e635b8e7d684446f683cde914399f8de5460dc6723"
    "63fa4300e3c2a1e6de9cc32300000000b4016504474e01bb0200210116000000"
    "742fe5a3e0003b002d5d00348cc42691c8b91ac7908be7e635b8e7d685e28768"
    "3cde914399f8de5460dc672363fa43011d1be020109cdc67000000006cbf8baa"
    "964240df0200210116000000742fe5a3e0003b002d5d00358cc426b1c8b91ac7"
    "908be7e635b8e7d687809f683cde914399f8de5460dc672363fa430154fa22f1"
    "0db14a8700000000a08ece54a2e123cc0200210116000000742fe5a3e0001d00"
    "1c5d00368cc426d1c8b91ac7908be7e635b8e7d6891eb7683cdddf0721800000"
    "194fe77b8383eba10004493c493c493c381e0000b6ec165714173b3003000000"
    "0004595a"
    # stream padding
    "0000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "000000000000000000000000"
)


@pytest.mark.parametrize("filetype", ("fileobj", "filename", "path"))
def test_read(filetype, tmp_path, data_pattern_locate):
    if filetype == "fileobj":
        filename = BytesIO(FILE_BYTES)
    else:
        filename = tmp_path / "archive.xz"
        filename.write_bytes(FILE_BYTES)
        if filetype == "filename":
            filename = os.fspath(filename)

    with XZFile(filename) as xzfile:
        assert xzfile._length == 400  # pylint: disable=protected-access
        assert xzfile.stream_boundaries == [0, 190]
        assert xzfile.block_boundaries == [0, 100, 190, 250, 310, 370]

        # read from start
        assert data_pattern_locate(xzfile.read(20)) == (0, 20)

        # read from middle of a block
        xzfile.seek(40)
        assert data_pattern_locate(xzfile.read(20)) == (40, 20)

        # read accross two blocks
        xzfile.seek(90)
        assert data_pattern_locate(xzfile.read(20)) == (90, 20)

        # read middle of an other block
        xzfile.seek(160)
        assert data_pattern_locate(xzfile.read(20)) == (160, 20)

        # read accross two streams
        xzfile.seek(180)
        assert data_pattern_locate(xzfile.read(20)) == (180, 20)

        # read middle of an other block
        xzfile.seek(320)
        assert data_pattern_locate(xzfile.read(20)) == (320, 20)

        # read accross two blocks
        xzfile.seek(360)
        assert data_pattern_locate(xzfile.read(20)) == (360, 20)

        # read until the end
        assert data_pattern_locate(xzfile.read()) == (380, 20)

        # go backward and read
        xzfile.seek(210)
        assert data_pattern_locate(xzfile.read(20)) == (210, 20)

        # read in previous stream (going backward from last read in that stream)
        xzfile.seek(60)
        assert data_pattern_locate(xzfile.read(20)) == (60, 20)

        # read all
        xzfile.seek(0)
        assert data_pattern_locate(xzfile.read()) == (0, 400)


@pytest.mark.parametrize("mode", ("r", "rb"))
def test_read_with_mode(mode, data_pattern_locate):
    filename = BytesIO(FILE_BYTES)

    with XZFile(filename, mode=mode) as xzfile:
        assert xzfile._length == 400  # pylint: disable=protected-access
        assert data_pattern_locate(xzfile.read(20)) == (0, 20)


def test_read_invalid_stream_padding():
    filename = BytesIO(FILE_BYTES + b"\x00" * 3)

    with pytest.raises(XZError) as exc_info:
        XZFile(filename)
    assert str(exc_info.value) == "file: invalid size"


def test_read_invalid_filename_type():
    with pytest.raises(TypeError) as exc_info:
        XZFile(42)
    assert (
        str(exc_info.value) == "filename must be a str, bytes, file or PathLike object"
    )


@pytest.mark.parametrize("data", (b"", b"\x00" * 100), ids=("empty", "only-padding"))
def test_read_no_stream(data):
    filename = BytesIO(data)

    with pytest.raises(XZError) as exc_info:
        XZFile(filename)
    assert str(exc_info.value) == "file: no streams"


@pytest.mark.parametrize(
    "mode",
    (
        "rt",
        "r+",
        "r+b",
        "r+t",
        "w",
        "wb",
        "wt",
        "w+",
        "w+b",
        "w+t",
        "x",
        "xb",
        "xt",
        "x+",
        "x+b",
        "x+t",
        "a",
        "ab",
        "at",
        "a+",
        "a+b",
        "a+t",
        "what-is-this",
    ),
)
def test_invalid_mode(mode):
    filename = BytesIO(FILE_BYTES)
    with pytest.raises(ValueError) as exc_info:
        XZFile(filename, mode)
    assert str(exc_info.value) == f"invalid mode: {mode}"
