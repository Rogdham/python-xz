from lzma import CHECK_CRC32, CHECK_CRC64, CHECK_NONE, CHECK_SHA256

import pytest

from xz.common import (
    XZError,
    create_xz_header,
    create_xz_index_footer,
    decode_mbi,
    encode_mbi,
    pad,
    parse_xz_footer,
    parse_xz_header,
    parse_xz_index,
    round_up,
)

MBI_CASE = tuple(
    pytest.param(value, data, id=hex(value))
    for value, data in (
        (0, "00"),
        (1, "01"),
        ((1 << 7) - 1, "7f"),
        (1 << 7, "8001"),
        ((1 << 7 * 2) - 1, "ff7f"),
        (1 << 7 * 2, "808001"),
        ((1 << 7 * 3) - 1, "ffff7f"),
        (1 << 7 * 3, "80808001"),
        ((1 << 7 * 10) - 1, "ffffffffffffffffff7f"),
        (1 << 7 * 10, "8080808080808080808001"),
        (9, "09"),
        (99, "63"),
        (999, "e707"),
        (9999, "8f4e"),
        (99999, "9f8d06"),
        (999999, "bf843d"),
        (9999999, "fface204"),
        (99999999, "ffc1d72f"),
        (999999999, "ff93ebdc03"),
    )
)


@pytest.mark.parametrize("value, data", MBI_CASE)
def test_encode_mbi(value, data):
    assert encode_mbi(value) == bytes.fromhex(data)


@pytest.mark.parametrize("value, data", MBI_CASE)
def test_decode_mbi(value, data):
    assert decode_mbi(bytes.fromhex(data) + b"\xff\x00" * 10) == (len(data) // 2, value)


@pytest.mark.parametrize("data", ("", "81828384"), ids=("empty", "truncated"))
def test_decode_mbi_invalid(data):
    with pytest.raises(XZError) as exc_info:
        decode_mbi(bytes.fromhex(data))
    assert str(exc_info.value) == "invalid mbi"


@pytest.mark.parametrize(
    "value, expected",
    ((0, 0), (1, 4), (2, 4), (3, 4), (4, 4), (5, 8), (6, 8), (7, 8), (8, 8)),
)
def test_round_up(value, expected):
    assert round_up(value) == expected


@pytest.mark.parametrize(
    "value, padding",
    (
        (0, ""),
        (1, "000000"),
        (2, "0000"),
        (3, "00"),
        (4, ""),
        (5, "000000"),
        (6, "0000"),
        (7, "00"),
        (8, ""),
    ),
)
def test_pad(value, padding):
    assert pad(value) == bytes.fromhex(padding)
    data = b"B" * value
    data += bytes.fromhex(padding)
    assert not len(data) % 4


XZ_HEADER_CASES = (
    pytest.param(CHECK_NONE, "fd377a585a000000ff12d941", id="check_none"),
    pytest.param(CHECK_CRC32, "fd377a585a0000016922de36", id="check_crc32"),
    pytest.param(CHECK_CRC64, "fd377a585a000004e6d6b446", id="check_crc64"),
    pytest.param(CHECK_SHA256, "fd377a585a00000ae1fb0ca1", id="check_sha256"),
)


@pytest.mark.parametrize("check, data", XZ_HEADER_CASES)
def test_create_xz_header(check, data):
    assert create_xz_header(check) == bytes.fromhex(data)


def test_create_xz_header_invalid_check():
    with pytest.raises(XZError) as exc_info:
        create_xz_header(17)
    assert str(exc_info.value) == "header check"


@pytest.mark.parametrize("check, data", XZ_HEADER_CASES)
def test_parse_xz_header(check, data):
    assert parse_xz_header(bytes.fromhex(data)) == check


@pytest.mark.parametrize(
    "data, message",
    (
        ("fd377a585a0000016922de3600", "header length"),
        ("f1377a585a000000ff12d941", "header magic"),
        ("fd377a585a0000016942de36", "header crc32"),
        ("fd377a585a0000110d32692b", "header flags"),
        ("fd377a585a0001012813c52f", "header flags"),
        ("fd377a585a00100138301c7c", "header flags"),
    ),
)
def test_parse_xz_header_invalid(data, message):
    with pytest.raises(XZError) as exc_info:
        parse_xz_header(bytes.fromhex(data))
    assert str(exc_info.value) == message


XZ_INDEX_CASES = (
    # all have check=1
    pytest.param([], "000000001cdf4421", id="empty"),
    pytest.param([(24, 4)], "000118046be9f0a5", id="one-small-block"),
    pytest.param([(2062, 20280)], "00018e10b89e010039f45fb1", id="one-big-block"),
    pytest.param(
        [(73, 60), (73, 60), (73, 60), (56, 30)],
        "0004493c493c493c381e0000b6ec1657",
        id="several-small-blocks",
    ),
    pytest.param(
        [(1, 2), (11, 2222), (1111, 22222222), (11111111, 2222222222222222)],
        "000401020bae11d7088eabcc0ac795a6058ec7abf196a3f903000000c9647142",
        id="several-blocks-various-sizes",
    ),
)


@pytest.mark.parametrize("records, data", XZ_INDEX_CASES)
def test_create_xz_index(records, data):
    assert create_xz_index_footer(1, records)[:-12] == bytes.fromhex(data)


@pytest.mark.parametrize("records, data", XZ_INDEX_CASES)
def test_parse_xz_index(records, data):
    assert parse_xz_index(bytes.fromhex(data)) == records


@pytest.mark.parametrize(
    "data, message",
    (
        ("0000001cdf4421", "index length"),
        ("420000001cdf4421", "index indicator"),
        ("000000001cdf4221", "index crc32"),
        ("000218043257b6a7", "index size"),
        ("000100043271eb27", "index record unpadded size"),
        ("000188047163b1d4", "index size"),
        ("000104002f70ea44", "index record uncompressed size"),
        ("000180180400420096a658c0", "index padding"),
    ),
)
def test_parse_xz_index_invalid(data, message):
    with pytest.raises(XZError) as exc_info:
        parse_xz_index(bytes.fromhex(data))
    assert str(exc_info.value) == message


XZ_FOOTER_CASES = (
    # all have backward_size=8 (i.e. no blocks)
    pytest.param(CHECK_NONE, "06729e7a010000000000595a", id="check_none"),
    pytest.param(CHECK_CRC32, "9042990d010000000001595a", id="check_crc32"),
    pytest.param(CHECK_CRC64, "1fb6f37d010000000004595a", id="check_crc64"),
    pytest.param(CHECK_SHA256, "189b4b9a01000000000a595a", id="check_sha256"),
)


@pytest.mark.parametrize("check, data", XZ_FOOTER_CASES)
def test_create_xz_footer(check, data):
    assert create_xz_index_footer(check, [])[-12:] == bytes.fromhex(data)


def test_create_xz_footer_invalid_check():
    with pytest.raises(XZError) as exc_info:
        create_xz_index_footer(17, [])
    assert str(exc_info.value) == "footer check"


@pytest.mark.parametrize("check, data", XZ_FOOTER_CASES)
def test_parse_xz_footer(check, data):
    assert parse_xz_footer(bytes.fromhex(data)) == (check, 8)


@pytest.mark.parametrize(
    "data, message",
    (
        ("009042990d010000000001595a", "footer length"),
        ("9042990d0100000000015959", "footer magic"),
        ("9042090d010000000001595a", "footer crc32"),
        ("f4522e10010000000011595a", "footer flags"),
        ("d1738214010000000101595a", "footer flags"),
        ("c1505b47010000001001595a", "footer flags"),
    ),
)
def test_parse_xz_footer_invalid(data, message):
    with pytest.raises(XZError) as exc_info:
        parse_xz_footer(bytes.fromhex(data))
    assert str(exc_info.value) == message
