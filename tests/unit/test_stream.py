from io import SEEK_CUR, SEEK_END, BytesIO
from typing import Callable, Tuple, cast
from unittest.mock import Mock, call

import pytest

from xz.common import XZError
from xz.io import IOProxy
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

# a stream with no blocks
STREAM_BYTES_EMPTY = bytes.fromhex(
    "fd377a585a0000016922de36000000001cdf44219042990d010000000001595a"
)


def test_parse(data_pattern_locate: Callable[[bytes], Tuple[int, int]]) -> None:
    fileobj = Mock(wraps=BytesIO(b"\xff" * 1000 + STREAM_BYTES + b"\xee" * 1000))
    fileobj.seek(-1000, SEEK_END)
    fileobj.method_calls.clear()

    # parse stream
    stream = XZStream.parse(fileobj)
    assert stream.check == 1
    assert len(stream) == 190
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


def test_parse_invalid_stream_flags_missmatch() -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000004e6d6b446000000001cdf44219042990d010000000001595a"
        )
    )
    fileobj.seek(0, SEEK_END)
    with pytest.raises(XZError) as exc_info:
        XZStream.parse(fileobj)
    assert str(exc_info.value) == "stream: inconsistent check value"


def test_parse_empty_block() -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a0000016922de360200210116000000742fe5a30000000000000000"
            "000111003b965f739042990d010000000001595a"
        )
    )
    fileobj.seek(0, SEEK_END)
    with pytest.raises(XZError) as exc_info:
        XZStream.parse(fileobj)
    assert str(exc_info.value) == "index record uncompressed size"


def test_parse_empty_stream() -> None:
    fileobj = BytesIO(STREAM_BYTES_EMPTY)
    fileobj.seek(0, SEEK_END)
    stream = XZStream.parse(fileobj)
    assert len(stream) == 0
    assert stream.block_boundaries == []


def test_write(data_pattern: bytes) -> None:
    # init with more size than what will be written at the end
    init_size = 1024
    assert len(STREAM_BYTES) < init_size

    fileobj = BytesIO(b"A" * init_size)

    with XZStream(cast(IOProxy, fileobj), 1) as stream:
        assert fileobj.getvalue() == b"A" * init_size

        assert stream.block_boundaries == []

        stream.change_block()
        assert stream.block_boundaries == []

        stream.write(data_pattern[:100])
        assert stream.block_boundaries == [0]

        stream.change_block()
        assert stream.block_boundaries == [0, 100]

        stream.write(data_pattern[100:190])
        assert stream.block_boundaries == [0, 100]

    assert fileobj.getvalue() == STREAM_BYTES


def test_write_from_existing_stream(data_pattern: bytes) -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a0000016922de360200210116000000742fe5a3e0006300415d0020"
            "9842100431d01ab2853283057ddb5924a128599cc9911a7fcff8d59c1f6f887b"
            "cee97b1f83f1808f005de273e1a6e99a7eac4f8f632b7e43bbf1da311dce5c00"
            "00000000e7c35efa0001596477f620019042990d010000000001595a"
        )
    )
    fileobj.seek(0, SEEK_END)
    with XZStream.parse(fileobj) as stream:
        assert stream.read() == data_pattern[:100]
        assert stream.block_boundaries == [0]

        stream.write(data_pattern[100:190])
        assert stream.block_boundaries == [0, 100]

    assert fileobj.getvalue() == STREAM_BYTES


def test_truncate_and_write(data_pattern: bytes) -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a0000016922de360200210116000000742fe5a3e0006300415d0020"
            "9842100431d01ab2853283057ddb5924a128599cc9911a7fcff8d59c1f6f887b"
            "cee97b1f83f1808f005de273e1a6e99a7eac4f8f632b7e43bbf1da311dce5c00"
            "00000000e7c35efa0200210116000000742fe5a30100025a5a5a0000407f8055"
            "00025964170300008d97067a3e300d8b020000000001595a"
        )
    )
    fileobj.seek(0, SEEK_END)
    with XZStream.parse(fileobj) as stream:
        assert stream.read() == data_pattern[:100] + b"ZZZ"
        assert stream.block_boundaries == [0, 100]

        stream.seek(100)
        stream.truncate()
        assert stream.block_boundaries == [0]

        stream.write(data_pattern[100:190])
        assert stream.block_boundaries == [0, 100]

    assert fileobj.getvalue() == STREAM_BYTES


def test_truncate_middle_block() -> None:
    fileobj = BytesIO(STREAM_BYTES)
    fileobj.seek(0, SEEK_END)
    with pytest.raises(ValueError) as exc_info:
        with XZStream.parse(fileobj) as stream:
            stream.truncate(80)
    assert str(exc_info.value) == "truncate"


def test_read_only_check() -> None:
    fileobj = BytesIO()

    with XZStream(cast(IOProxy, fileobj), 1) as stream:
        with pytest.raises(AttributeError):
            stream.check = 4  # type: ignore[misc]


def test_change_filters() -> None:
    fileobj = BytesIO()

    with XZStream(cast(IOProxy, fileobj), 1) as stream:
        stream.write(b"aa")
        stream.change_block()
        stream.filters = [{"id": 3, "dist": 1}, {"id": 33}]
        stream.write(b"bb")
        stream.change_block()
        stream.write(b"cc")
        stream.change_block()
        stream.write(b"dd")

    assert fileobj.getvalue() == bytes.fromhex(
        # header
        "fd377a585a0000016922de36"
        # block 1
        "0200210116000000742fe5a30100016161000000d7198a07"
        # block 2
        "0200210116000000742fe5a30100016262000000ae1baeb5"
        # block 3 (changed filters)
        "02010301002101167920c4ee0100016300000000791ab2db"
        # block 4 (changed filters)
        "02010301002101167920c4ee01000164000000001d19970a"
        # index
        "0004160216021602160200008a2bb83b"
        # footer
        "9be35140030000000001595a"
    )


def test_change_preset() -> None:
    fileobj = BytesIO()

    with XZStream(cast(IOProxy, fileobj), 1) as stream:
        stream.write(b"aa")
        stream.change_block()
        stream.preset = 9
        stream.write(b"bb")
        stream.change_block()
        stream.write(b"cc")
        stream.change_block()
        stream.write(b"dd")

    assert fileobj.getvalue() == bytes.fromhex(
        # header
        "fd377a585a0000016922de36"
        # block 1
        "0200210116000000742fe5a30100016161000000d7198a07"
        # block 2
        "0200210116000000742fe5a30100016262000000ae1baeb5"
        # block 3 (changed preset)
        "020021011c00000010cf58cc0100016363000000791ab2db"
        # block 4 (changed preset)
        "020021011c00000010cf58cc01000164640000001d19970a"
        # index
        "0004160216021602160200008a2bb83b"
        # footer
        "9be35140030000000001595a"
    )
