from io import SEEK_CUR, SEEK_END, BytesIO
from unittest.mock import Mock, call

import pytest

from xz.common import XZError
from xz.stream import XZStream

# a stream with two blocks (lengths: 100, 90)
STREAM_BYTES = bytes.fromhex(
    "fd377a585a0000016922de360200210116000000742fe5a3e0006300415d0020"
    "9842100431d01ab2853283057ddb5924a128599cc9911a7fcff8d59c1f6f887b"
    "cee97b1f83f1808f005de273e1a6e99a7eac4f8f632b7e43bbf1da311dce5c00"
    "00000000e7c35efa0200210116000000742fe5a3e00059003d5d00320cc42641"
    "c8b91ac7908be7e635b8e7d681d74b683cde914399f8de5460dc672363f1e067"
    "5a3ebac9f427ecbebcb94552c0dba85b26950f0ac98b22390000000031f4ee87"
    "00025964555a0000041276283e300d8b020000000001595a"
)


def test_parse(data_pattern_locate):
    fileobj = Mock(wraps=BytesIO(b"\xff" * 1000 + STREAM_BYTES + b"\xee" * 1000))
    fileobj.seek(-1000, SEEK_END)  # move at the end of the stream
    fileobj.method_calls.clear()

    # parse stream
    stream = XZStream.parse(fileobj)
    assert stream.check == 1
    assert stream._length == 190  # pylint: disable=protected-access
    assert stream.block_boundaries == [0, 100]

    # make sure we don't read the blocks
    assert fileobj.method_calls == [
        call.seek(-12, SEEK_CUR),
        call.read(12),
        call.seek(-24, SEEK_CUR),
        call.read(12),
        call.seek(-204, SEEK_CUR),  # blocks are skipped over here
        call.read(12),
        call.seek(-12, SEEK_CUR),
    ]

    # fileobj should be at the begining of the stream
    assert fileobj.tell() == 1000

    # read from start
    assert data_pattern_locate(stream.read(20)) == (0, 20)

    # read from middle of a block
    stream.seek(40)
    assert data_pattern_locate(stream.read(20)) == (40, 20)

    # read accross two blocks
    stream.seek(90)
    assert data_pattern_locate(stream.read(20)) == (90, 20)

    # read middle of an other block
    stream.seek(160)
    assert data_pattern_locate(stream.read(20)) == (160, 20)

    # go backward and read
    stream.seek(130)
    assert data_pattern_locate(stream.read(20)) == (130, 20)

    # read in previous block (going backward from last read in that block)
    stream.seek(60)
    assert data_pattern_locate(stream.read(20)) == (60, 20)

    # read until end
    stream.seek(170)
    assert data_pattern_locate(stream.read()) == (170, 20)


def test_invalid_stream_flags_missmatch():
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000004e6d6b446000000001cdf44219042990d010000000001595a"
        )
    )
    fileobj.seek(0, SEEK_END)  # move at the end of the stream
    with pytest.raises(XZError) as exc_info:
        XZStream.parse(fileobj)
    assert str(exc_info.value) == "stream: inconsistent check value"
