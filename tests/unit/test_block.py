from io import SEEK_SET, BytesIO
from unittest.mock import Mock, call

import pytest

from xz.block import XZBlock
from xz.common import XZError
from xz.io import IOProxy

BLOCK_BYTES = bytes.fromhex(
    "0200210116000000742fe5a3e0006300415d00209842100431d01ab285328305"
    "7ddb5924a128599cc9911a7fcff8d59c1f6f887bcee97b1f83f1808f005de273"
    "e1a6e99a7eac4f8f632b7e43bbf1da311dce5c0000000000e7c35efa"
)


@pytest.fixture
def fileobj():
    proxy = IOProxy(BytesIO(BLOCK_BYTES), 0, 92)
    mock = Mock(wraps=proxy)
    mock.__class__ = IOProxy
    mock._length = proxy._length  # pylint: disable=protected-access
    yield mock


# pylint: disable=redefined-outer-name


def test_read_all(fileobj, data_pattern_locate):
    block = XZBlock(fileobj, 1, 89, 100)
    block.compressed_read_size = 17
    assert block.tell() == 0
    assert data_pattern_locate(block.read()) == (0, 100)

    assert fileobj.method_calls == [
        call.seek(0, SEEK_SET),
        call.read(5),  # xz padding is 12 bytes
        call.seek(5, SEEK_SET),
        call.read(17),
        call.seek(22, SEEK_SET),
        call.read(17),
        call.seek(39, SEEK_SET),
        call.read(17),
        call.seek(56, SEEK_SET),
        call.read(17),
        call.seek(73, SEEK_SET),
        call.read(17),
        # below is not needed to get the data
        # but needed to perform various checks
        # see other tests
        call.seek(90, SEEK_SET),
        call.read(17),
    ]


def test_seek_forward(fileobj, data_pattern_locate):
    block = XZBlock(fileobj, 1, 89, 100)
    block.compressed_read_size = 17
    assert block.tell() == 0

    block.seek(0)
    assert block.tell() == 0
    assert not fileobj.method_calls  # no file access
    assert data_pattern_locate(block.read(4)) == (0, 4)
    assert block.tell() == 4
    assert fileobj.method_calls == [
        call.seek(0, SEEK_SET),
        call.read(5),  # xz padding is 12 bytes
        call.seek(5, SEEK_SET),
        call.read(17),
        call.seek(22, SEEK_SET),
        call.read(17),
    ]
    fileobj.method_calls.clear()

    block.seek(10)
    assert block.tell() == 10
    assert not fileobj.method_calls  # no file access
    assert data_pattern_locate(block.read(4)) == (10, 4)
    assert block.tell() == 14
    assert not fileobj.method_calls  # no file access

    block.seek(30)
    assert block.tell() == 30
    assert fileobj.method_calls == [
        call.seek(39, SEEK_SET),
        call.read(17),
    ]
    fileobj.method_calls.clear()
    assert data_pattern_locate(block.read(4)) == (30, 4)
    assert block.tell() == 34
    assert not fileobj.method_calls  # no file access

    block.seek(60)
    assert block.tell() == 60
    assert fileobj.method_calls == [
        call.seek(56, SEEK_SET),
        call.read(17),
    ]
    fileobj.method_calls.clear()
    assert data_pattern_locate(block.read(4)) == (60, 4)
    assert block.tell() == 64
    assert not fileobj.method_calls  # no file access


def test_seek_backward(fileobj, data_pattern_locate):
    block = XZBlock(fileobj, 1, 89, 100)
    block.compressed_read_size = 17
    assert block.tell() == 0

    block.seek(60)
    assert block.tell() == 60
    assert fileobj.method_calls == [
        call.seek(0, SEEK_SET),
        call.read(5),  # xz padding is 12 bytes
        call.seek(5, SEEK_SET),
        call.read(17),
        call.seek(22, SEEK_SET),
        call.read(17),
        call.seek(39, SEEK_SET),
        call.read(17),
        call.seek(56, SEEK_SET),
        call.read(17),
    ]
    fileobj.method_calls.clear()
    fileobj.method_calls.clear()

    block.seek(40)
    assert block.tell() == 40
    assert fileobj.method_calls == [
        call.seek(0, SEEK_SET),
        call.read(5),  # xz padding is 12 bytes
        call.seek(5, SEEK_SET),
        call.read(17),
        call.seek(22, SEEK_SET),
        call.read(17),
        call.seek(39, SEEK_SET),
        call.read(17),
    ]
    fileobj.method_calls.clear()
    assert data_pattern_locate(block.read(4)) == (40, 4)
    assert block.tell() == 44
    assert not fileobj.method_calls  # no file access

    block.seek(20)
    assert block.tell() == 20
    assert fileobj.method_calls == [
        call.seek(0, SEEK_SET),
        call.read(5),  # xz padding is 12 bytes
        call.seek(5, SEEK_SET),
        call.read(17),
        call.seek(22, SEEK_SET),
        call.read(17),
    ]
    fileobj.method_calls.clear()
    assert data_pattern_locate(block.read(4)) == (20, 4)
    assert block.tell() == 24
    assert fileobj.method_calls == [
        call.seek(39, SEEK_SET),
        call.read(17),
    ]


def test_wrong_uncompressed_size_too_small(fileobj, data_pattern_locate):
    block = XZBlock(fileobj, 1, 89, 99)
    block.compressed_read_size = 17

    # read all but last byte
    assert data_pattern_locate(block.read(98)) == (0, 98)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: error while decompressing: Corrupt input data"


def test_wrong_uncompressed_size_too_big(fileobj, data_pattern_locate):
    block = XZBlock(fileobj, 1, 89, 101)
    block.compressed_read_size = 17

    # read all but last byte
    assert data_pattern_locate(block.read(100)) == (0, 100)

    # read last byte
    print("-" * 10)
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: error while decompressing: Corrupt input data"


def test_wrong_block_padding(data_pattern_locate):
    fileobj = IOProxy(BytesIO(BLOCK_BYTES[:-5] + b"\xff" + BLOCK_BYTES[-4:]), 0, 92)
    block = XZBlock(fileobj, 1, 89, 100)
    block.compressed_read_size = 17

    # read all but last byte
    assert data_pattern_locate(block.read(99)) == (0, 99)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: error while decompressing: Corrupt input data"


def test_wrong_check(data_pattern_locate):
    fileobj = IOProxy(BytesIO(BLOCK_BYTES[:-4] + b"\xff" * 4), 0, 92)

    block = XZBlock(fileobj, 1, 89, 100)
    block.compressed_read_size = 17

    # read all but last byte
    assert data_pattern_locate(block.read(99)) == (0, 99)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: error while decompressing: Corrupt input data"


def test_truncated_data(fileobj):
    block = XZBlock(fileobj, 1, 89, 100)
    block.compressed_read_size = 17
    block.compressed_fileobj = IOProxy(
        BytesIO(
            bytes.fromhex(
                # header
                "fd377a585a0000016922de36"
                # one block (truncated)
                "0200210116000000742fe5a301000941"
            )
        ),
        0,
        28,
    )

    with pytest.raises(XZError) as exc_info:
        block.read()
    assert str(exc_info.value) == "block: data eof"


def test_decompressor_eof(data_pattern_locate):
    fileobj = IOProxy(
        BytesIO(
            bytes.fromhex(
                # one block
                "0200210116000000742fe5a301000941"
                "6130416131416132410000004e4aa467"
                # index
                "00011e0aea6312149042990d0100"
                # stream footer
                "00000001595a"
            )
        ),
        0,
        52,
    )

    # real uncompressed size is 10, not 11
    # it is changed to trigger the error case we are testing here
    block = XZBlock(fileobj, 1, 30, 11)
    block.compressed_read_size = 17

    # read all but last byte
    assert data_pattern_locate(block.read(10)) == (0, 10)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: decompressor eof"
