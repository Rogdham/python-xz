from io import SEEK_SET, BytesIO, UnsupportedOperation
from typing import Callable, Iterator, Tuple, cast
from unittest.mock import Mock, call

import pytest

import xz.block as block_module
from xz.block import BlockRead, XZBlock
from xz.common import XZError, create_xz_header, create_xz_index_footer
from xz.io import IOAbstract, IOStatic

BLOCK_BYTES = bytes.fromhex(
    "0200210116000000742fe5a3e0006300415d00209842100431d01ab285328305"
    "7ddb5924a128599cc9911a7fcff8d59c1f6f887bcee97b1f83f1808f005de273"
    "e1a6e99a7eac4f8f632b7e43bbf1da311dce5c0000000000e7c35efa"
)


def create_fileobj(data: bytes) -> Mock:
    raw = BytesIO(data)
    mock = Mock(wraps=raw)
    mock.__class__ = cast(Mock, IOAbstract)  # needs to be subclass of IOAbstract
    mock.__len__ = lambda _: len(raw.getvalue())
    return mock


@pytest.fixture
def fileobj() -> Iterator[Mock]:
    yield create_fileobj(BLOCK_BYTES)


@pytest.fixture
def fileobj_empty() -> Iterator[Mock]:
    yield create_fileobj(b"")


@pytest.fixture(autouse=True)
def patch_buffer_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(BlockRead, "read_size", 17)


@pytest.fixture
def compressor(monkeypatch: pytest.MonkeyPatch) -> Iterator[Mock]:
    mock = Mock()
    monkeypatch.setattr(block_module, "LZMACompressor", mock)
    yield mock.return_value


# pylint: disable=redefined-outer-name


#
# read
#


def test_read_all(
    fileobj: Mock, data_pattern_locate: Callable[[bytes], Tuple[int, int]]
) -> None:
    block = XZBlock(fileobj, 1, 89, 100)
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


def test_read_seek_forward(
    fileobj: Mock, data_pattern_locate: Callable[[bytes], Tuple[int, int]]
) -> None:
    block = XZBlock(fileobj, 1, 89, 100)
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
    assert not fileobj.method_calls  # no file access
    assert data_pattern_locate(block.read(4)) == (30, 4)
    assert block.tell() == 34
    assert fileobj.method_calls == [
        call.seek(39, SEEK_SET),
        call.read(17),
    ]
    fileobj.method_calls.clear()

    block.seek(60)
    assert block.tell() == 60
    assert not fileobj.method_calls  # no file access
    assert data_pattern_locate(block.read(4)) == (60, 4)
    assert block.tell() == 64
    assert fileobj.method_calls == [
        call.seek(56, SEEK_SET),
        call.read(17),
    ]
    fileobj.method_calls.clear()


def test_read_seek_backward(
    fileobj: Mock, data_pattern_locate: Callable[[bytes], Tuple[int, int]]
) -> None:
    block = XZBlock(fileobj, 1, 89, 100)
    assert block.tell() == 0

    block.seek(60)
    assert block.tell() == 60
    assert not fileobj.method_calls  # no file access

    block.seek(40)
    assert block.tell() == 40
    assert not fileobj.method_calls  # no file access
    assert data_pattern_locate(block.read(4)) == (40, 4)
    assert block.tell() == 44
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
    assert not fileobj.method_calls  # no file access

    block.seek(20)
    assert block.tell() == 20
    assert not fileobj.method_calls  # no file access
    assert data_pattern_locate(block.read(4)) == (20, 4)
    assert block.tell() == 24
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


def test_read_wrong_uncompressed_size_too_small(
    fileobj: Mock, data_pattern_locate: Callable[[bytes], Tuple[int, int]]
) -> None:
    block = XZBlock(fileobj, 1, 89, 99)

    # read all but last byte
    assert data_pattern_locate(block.read(98)) == (0, 98)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: error while decompressing: Corrupt input data"


def test_read_wrong_uncompressed_size_too_big(
    fileobj: Mock, data_pattern_locate: Callable[[bytes], Tuple[int, int]]
) -> None:
    block = XZBlock(fileobj, 1, 89, 101)

    # read all but last byte
    assert data_pattern_locate(block.read(100)) == (0, 100)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: error while decompressing: Corrupt input data"


def test_read_wrong_block_padding(
    data_pattern_locate: Callable[[bytes], Tuple[int, int]]
) -> None:
    fileobj = IOStatic(BLOCK_BYTES[:-5] + b"\xff" + BLOCK_BYTES[-4:])
    block = XZBlock(fileobj, 1, 89, 100)

    # read all but last byte
    assert data_pattern_locate(block.read(99)) == (0, 99)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: error while decompressing: Corrupt input data"


def test_read_wrong_check(
    data_pattern_locate: Callable[[bytes], Tuple[int, int]]
) -> None:
    fileobj = IOStatic(BLOCK_BYTES[:-4] + b"\xff" * 4)

    block = XZBlock(fileobj, 1, 89, 100)

    # read all but last byte
    assert data_pattern_locate(block.read(99)) == (0, 99)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: error while decompressing: Corrupt input data"


def test_read_truncated_data() -> None:
    fileobj = create_fileobj(
        bytes.fromhex(
            # header
            "fd377a585a0000016922de36"
            # one block (truncated)
            "0200210116000000742fe5a301000941"
        )
    )

    block = XZBlock(fileobj, 1, 89, 100)

    with pytest.raises(XZError) as exc_info:
        block.read()
    assert str(exc_info.value) == "block: data eof"


def test_read_decompressor_eof(
    data_pattern_locate: Callable[[bytes], Tuple[int, int]]
) -> None:
    fileobj = IOStatic(
        bytes.fromhex(
            # one block
            "0200210116000000742fe5a301000941"
            "6130416131416132410000004e4aa467"
            # index
            "00011e0aea6312149042990d0100"
            # stream footer
            "00000001595a"
        )
    )

    # real uncompressed size is 10, not 11
    # it is changed to trigger the error case we are testing here
    block = XZBlock(fileobj, 1, 30, 11)

    # read all but last byte
    assert data_pattern_locate(block.read(10)) == (0, 10)

    # read last byte
    with pytest.raises(XZError) as exc_info:
        block.read(1)
    assert str(exc_info.value) == "block: decompressor eof"


#
# writable
#


def test_writable(fileobj: Mock) -> None:
    block = XZBlock(fileobj, 1, 89, 100)
    assert not block.writable()


def test_writable_empty(fileobj_empty: Mock) -> None:
    block = XZBlock(fileobj_empty, 1, 0, 0)
    assert block.writable()


#
# write
#


def test_write_once(fileobj_empty: Mock) -> None:
    with XZBlock(fileobj_empty, 1, 0, 0) as block:
        block.write(b"Hello, world!\n")
        assert block.tell() == 14
        assert fileobj_empty.method_calls == [
            call.seek(0),
            call.write(b"\x02\x00!\x01\x16\x00\x00\x00t/\xe5\xa3"),
        ]
        fileobj_empty.reset_mock()

    assert block.unpadded_size == 34
    assert block.uncompressed_size == 14

    assert fileobj_empty.method_calls == [
        call.seek(12),
        call.write(b"\x01\x00\rHello, world!\n\x00\x00\x00\x18\xa7U{"),
    ]


def test_write_multiple(fileobj_empty: Mock) -> None:
    with XZBlock(fileobj_empty, 1, 0, 0) as block:
        block.write(b"Hello,")
        assert block.tell() == 6
        assert fileobj_empty.method_calls == [
            call.seek(0),
            call.write(b"\x02\x00!\x01\x16\x00\x00\x00t/\xe5\xa3"),
        ]
        fileobj_empty.reset_mock()

        block.write(b" world!\n")
        assert block.tell() == 14
        assert not fileobj_empty.method_calls  # buffered

        block.write(b"A" * 3_000_000)
        assert block.tell() == 3_000_014
        assert fileobj_empty.method_calls  # not buffered

    assert block.unpadded_size == 540
    assert block.uncompressed_size == 3_000_014

    assert fileobj_empty.method_calls  # flushing compressor


@pytest.mark.parametrize("pos", [0, 42, 100, 200])
def test_write_existing(fileobj: Mock, pos: int) -> None:
    block = XZBlock(fileobj, 1, 89, 100)
    block.seek(pos)
    with pytest.raises(UnsupportedOperation):
        # block is not empty, so not writable
        block.write(b"a")


def test_write_compressor_error_0(fileobj_empty: Mock, compressor: Mock) -> None:
    compressor.compress.return_value = create_xz_header(0)
    with XZBlock(fileobj_empty, 1, 0, 0) as block:
        with pytest.raises(XZError) as exc_info:
            block.write(b"Hello, world!\n")
    assert str(exc_info.value) == "block: compressor header"


def test_write_compressor_error_1(fileobj_empty: Mock, compressor: Mock) -> None:
    compressor.compress.return_value = create_xz_header(1)
    compressor.flush.return_value = create_xz_index_footer(0, [(13, 37), (4, 2)])
    with pytest.raises(XZError) as exc_info:
        with XZBlock(fileobj_empty, 1, 0, 0) as block:
            block.write(b"Hello, world!\n")
    assert str(exc_info.value) == "block: compressor footer check"


def test_write_compressor_error_2(fileobj_empty: Mock, compressor: Mock) -> None:
    compressor.compress.return_value = create_xz_header(1)
    compressor.flush.return_value = create_xz_index_footer(1, [(13, 37), (4, 2)])
    with pytest.raises(XZError) as exc_info:
        with XZBlock(fileobj_empty, 1, 0, 0) as block:
            block.write(b"Hello, world!\n")
    assert str(exc_info.value) == "block: compressor index records length"


def test_write_compressor_error_3(fileobj_empty: Mock, compressor: Mock) -> None:
    compressor.compress.return_value = create_xz_header(1)
    compressor.flush.return_value = create_xz_index_footer(1, [(34, 1337)])
    with pytest.raises(XZError) as exc_info:
        with XZBlock(fileobj_empty, 1, 0, 0) as block:
            block.write(b"Hello, world!\n")
    assert str(exc_info.value) == "block: compressor uncompressed size"


#
# truncate
#


def test_truncate_empty_zero(fileobj_empty: Mock) -> None:
    with XZBlock(fileobj_empty, 1, 0, 0) as block:
        block.truncate(0)
        assert block.tell() == 0
        assert not fileobj_empty.method_calls

    assert block.unpadded_size == 0
    assert block.uncompressed_size == 0

    assert not fileobj_empty.method_calls


def test_truncate_empty_fill(fileobj_empty: Mock) -> None:
    with XZBlock(fileobj_empty, 1, 0, 0) as block:
        block.truncate(42)
        assert block.tell() == 0
        assert fileobj_empty.method_calls == [
            call.seek(0),
            call.write(b"\x02\x00!\x01\x16\x00\x00\x00t/\xe5\xa3"),
        ]
        fileobj_empty.reset_mock()

    assert block.unpadded_size == 30
    assert block.uncompressed_size == 42

    assert fileobj_empty.method_calls == [
        call.seek(12),
        call.write(b"\xe0\x00)\x00\x06]\x00\x00n,GH\x00\x00\x00\x00\xfb(o\xe4"),
    ]


@pytest.mark.parametrize("size", [0, 42, 100, 200])
def test_truncate_existing(fileobj: Mock, size: int) -> None:
    block = XZBlock(fileobj, 1, 89, 100)
    with pytest.raises(UnsupportedOperation):
        # block is not empty, so not writable
        block.truncate(size)
