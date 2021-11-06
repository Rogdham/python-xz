from io import BytesIO
import lzma
from pathlib import Path
from typing import List, Optional

import pytest

from xz.open import xz_open

# a stream with two blocks (lengths: 10, 3)
# one UTF8 character is between the two blocks
STREAM_BYTES = bytes.fromhex(
    "fd377a585a000004e6d6b446"
    "0200210116000000742fe5a3010009e299a5207574663820e2000000404506004bafe33d"
    "0200210116000000742fe5a301000299a50a0000c6687a2b8dbda0cf"
    "0002220a1b0300001b1c3777"
    "b1c467fb020000000004595a"
)


#
# read
#


def test_mode_rb() -> None:
    fileobj = BytesIO(STREAM_BYTES)

    with xz_open(fileobj, "rb") as xzfile:
        assert len(xzfile) == 13
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0, 10]

        assert xzfile.read() == b"\xe2\x99\xa5 utf8 \xe2\x99\xa5\n"

        assert xzfile.seek(9) == 9
        assert xzfile.read() == b"\xe2\x99\xa5\n"


def test_mode_rt() -> None:
    fileobj = BytesIO(STREAM_BYTES)

    with xz_open(fileobj, "rt") as xzfile:
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0, 10]

        assert xzfile.read() == "♥ utf8 ♥\n"

        assert xzfile.seek(9) == 9
        assert xzfile.read() == "♥\n"


def test_mode_rt_file(tmp_path: Path) -> None:
    file_path = tmp_path / "file.xz"
    file_path.write_bytes(STREAM_BYTES)

    with file_path.open("rb") as fin:
        with xz_open(fin, "rt") as xzfile:
            assert xzfile.stream_boundaries == [0]
            assert xzfile.block_boundaries == [0, 10]
            assert xzfile.fileno() == fin.fileno()

            assert xzfile.read() == "♥ utf8 ♥\n"

            assert xzfile.seek(9) == 9
            assert xzfile.read() == "♥\n"


@pytest.mark.parametrize(
    "encoding, expected",
    (
        pytest.param("utf8", "еñϲоԺε", id="utf8"),
        pytest.param("latin1", "ÐµÃ±Ï²Ð¾ÔºÎµ", id="latin1"),
    ),
)
def test_mode_rt_encoding(encoding: str, expected: str) -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000000ff12d9410200210116000000742fe5a301000bd0b5c3b1cf"
            "b2d0bed4baceb50000011c0c5da447cf06729e7a010000000000595a"
        )
    )
    with xz_open(fileobj, "rt", encoding=encoding) as xzfile:
        assert xzfile.read() == expected


@pytest.mark.parametrize(
    "errors, expected",
    (
        pytest.param(None, None, id="None"),
        pytest.param("strict", None, id="strict"),
        pytest.param("ignore", "encoding", id="ignore"),
        pytest.param("replace", "en�co�di�ng", id="replace"),
        pytest.param(
            "backslashreplace", r"en\x99co\x98di\x97ng", id="backslashreplace"
        ),
    ),
)
def test_mode_rt_encoding_errors(
    errors: Optional[str], expected: Optional[str]
) -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000000ff12d9410200210116000000742fe5a301000a656e99636f"
            "986469976e67000000011b0b39a7621e06729e7a010000000000595a"
        )
    )

    with xz_open(fileobj, "rt", errors=errors) as xzfile:
        if expected is None:
            with pytest.raises(ValueError):
                xzfile.read()
        else:
            assert xzfile.read() == expected


@pytest.mark.parametrize(
    "newline, expected",
    (
        pytest.param(None, ["a\n", "b\n", "c\n", "d"], id="None"),
        pytest.param("", ["a\n", "b\r", "c\r\n", "d"], id="''"),
        pytest.param("\n", ["a\n", "b\rc\r\n", "d"], id="'\n'"),
        pytest.param("\r", ["a\nb\r", "c\r", "\nd"], id="'\r'"),
        pytest.param("\r\n", ["a\nb\rc\r\n", "d"], id="'\r\n'"),
    ),
)
def test_mode_rt_newline(newline: Optional[str], expected: List[str]) -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000000ff12d9410200210116000000742fe5a3010007610a620d63"
            "0d0a64000001180840a546ac06729e7a010000000000595a"
        )
    )

    with xz_open(fileobj, "rt", newline=newline) as xzfile:
        assert xzfile.readlines() == expected


def test_mode_rb_encoding() -> None:
    fileobj = BytesIO(STREAM_BYTES)
    with pytest.raises(ValueError):
        xz_open(fileobj, "rb", encoding="latin1")


def test_mode_rb_encoding_errors() -> None:
    fileobj = BytesIO(STREAM_BYTES)
    with pytest.raises(ValueError):
        xz_open(fileobj, "rb", errors="ignore")


def test_mode_rb_newline() -> None:
    fileobj = BytesIO(STREAM_BYTES)
    with pytest.raises(ValueError):
        xz_open(fileobj, "rb", newline="\n")


#
# write
#

TEST_MODE_W_CHECK_BYTES = bytes.fromhex(
    # stream 1
    "fd377a585a0000016922de36"
    "0200210116000000742fe5a3010001ceb1000000256bc6a8"
    "00011602d06110d2"
    "9042990d010000000001595a"
    # stream 2
    "fd377a585a0000016922de36"
    "0200210116000000742fe5a3010001ceb20000009f3acf31"
    "00011602d06110d2"
    "9042990d010000000001595a"
    # stream 3 (changed check)
    "fd377a585a000004e6d6b446"
    "0200210116000000742fe5a3010001ceb3000000ab6cffc6b19a1d23"
    "00011a02dc2ea57e"
    "1fb6f37d010000000004595a"
    # stream 4 (changed check)
    "fd377a585a000004e6d6b446"
    "0200210116000000742fe5a3010001ceb4000000accd9792dc23671f"
    "00011a02dc2ea57e"
    "1fb6f37d010000000004595a"
)


def test_mode_wb_check() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wb", check=1) as xzfile:
        xzfile.write(b"\xce\xb1")
        xzfile.change_stream()
        xzfile.check = 4
        xzfile.write(b"\xce\xb2")
        xzfile.change_stream()
        xzfile.write(b"\xce\xb3")
        xzfile.change_stream()
        xzfile.write(b"\xce\xb4")

    assert fileobj.getvalue() == TEST_MODE_W_CHECK_BYTES


def test_mode_wt_check() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", check=1) as xzfile:
        xzfile.write("α")
        xzfile.change_stream()
        xzfile.check = 4
        xzfile.write("β")
        xzfile.change_stream()
        xzfile.write("γ")
        xzfile.change_stream()
        xzfile.write("δ")

    assert fileobj.getvalue() == TEST_MODE_W_CHECK_BYTES


TEST_MODE_W_FILTERS_BYTES = bytes.fromhex(
    ## stream 1
    # header
    "fd377a585a0000016922de36"
    # block 1
    "0200210116000000742fe5a3010001ceb1000000256bc6a8"
    # block 2
    "0200210116000000742fe5a3010001ceb20000009f3acf31"
    # block 3 (changed filters)
    "02010301002101167920c4ee010001cee5000000090ac846"
    # block 4 (changed filters)
    "02010301002101167920c4ee010001cee6000000aa9facd8"
    # index
    "0004160216021602160200008a2bb83b"
    # footer
    "9be35140030000000001595a"
    ## stream 2
    # header
    "fd377a585a0000016922de36"
    # block 1 (changed filters)
    "02010301002101167920c4ee010001cee70000003cafabaf"
    # block 2 (changed filters)
    "02010301002101167920c4ee010001cee800000086fea236"
    # index
    "00021602160200008ba0042b"
    # footer
    "3e300d8b020000000001595a"
    ## stream 3
    # header
    "fd377a585a0000016922de36"
    # block 1 (changed filters)
    "02010301002101167920c4ee010001cee900000010cea541"
    # block 2 (changed filters)
    "02010301002101167920c4ee010001ceea00000081d31ad1"
    # index
    "00021602160200008ba0042b"
    # footer
    "3e300d8b020000000001595a"
)


def test_mode_wb_filters() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wb", check=1) as xzfile:
        xzfile.write(b"\xce\xb1")
        xzfile.change_block()
        xzfile.filters = [{"id": 3, "dist": 1}, {"id": 33}]
        xzfile.write(b"\xce\xb2")
        xzfile.change_block()
        xzfile.write(b"\xce\xb3")
        xzfile.change_block()
        xzfile.write(b"\xce\xb4")
        xzfile.change_stream()
        xzfile.write(b"\xce\xb5")
        xzfile.change_block()
        xzfile.write(b"\xce\xb6")
        xzfile.change_stream()
        xzfile.write(b"\xce\xb7")
        xzfile.change_block()
        xzfile.write(b"\xce\xb8")

    assert fileobj.getvalue() == TEST_MODE_W_FILTERS_BYTES


def test_mode_wt_filters() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", check=1) as xzfile:
        xzfile.write("α")
        xzfile.change_block()
        xzfile.filters = [{"id": 3, "dist": 1}, {"id": 33}]
        xzfile.write("β")
        xzfile.change_block()
        xzfile.write("γ")
        xzfile.change_block()
        xzfile.write("δ")
        xzfile.change_stream()
        xzfile.write("ε")
        xzfile.change_block()
        xzfile.write("ζ")
        xzfile.change_stream()
        xzfile.write("η")
        xzfile.change_block()
        xzfile.write("θ")

    assert fileobj.getvalue() == TEST_MODE_W_FILTERS_BYTES


TEST_MODE_W_PRESET_BYTES = bytes.fromhex(
    ## stream 1
    # header
    "fd377a585a0000016922de36"
    # block 1
    "0200210116000000742fe5a3010001ceb1000000256bc6a8"
    # block 2
    "0200210116000000742fe5a3010001ceb20000009f3acf31"
    # block 3 (changed preset)
    "020021011c00000010cf58cc010001ceb3000000090ac846"
    # block 4 (changed preset)
    "020021011c00000010cf58cc010001ceb4000000aa9facd8"
    # index
    "0004160216021602160200008a2bb83b"
    # footer
    "9be35140030000000001595a"
    ## stream 2
    # header
    "fd377a585a0000016922de36"
    # block 1 (changed preset)
    "020021011c00000010cf58cc010001ceb50000003cafabaf"
    # block 2 (changed preset)
    "020021011c00000010cf58cc010001ceb600000086fea236"
    # index
    "00021602160200008ba0042b"
    # footer
    "3e300d8b020000000001595a"
    ## stream 3
    # header
    "fd377a585a0000016922de36"
    # block 1 (changed preset)
    "020021011c00000010cf58cc010001ceb700000010cea541"
    # block 2 (changed preset)
    "020021011c00000010cf58cc010001ceb800000081d31ad1"
    # index
    "00021602160200008ba0042b"
    # footer
    "3e300d8b020000000001595a"
)


def test_mode_wb_preset() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wb", check=1) as xzfile:
        xzfile.write(b"\xce\xb1")
        xzfile.change_block()
        xzfile.preset = 9
        xzfile.write(b"\xce\xb2")
        xzfile.change_block()
        xzfile.write(b"\xce\xb3")
        xzfile.change_block()
        xzfile.write(b"\xce\xb4")
        xzfile.change_stream()
        xzfile.write(b"\xce\xb5")
        xzfile.change_block()
        xzfile.write(b"\xce\xb6")
        xzfile.change_stream()
        xzfile.write(b"\xce\xb7")
        xzfile.change_block()
        xzfile.write(b"\xce\xb8")

    assert fileobj.getvalue() == TEST_MODE_W_PRESET_BYTES


def test_mode_wt_preset() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", check=1) as xzfile:
        xzfile.write("α")
        xzfile.change_block()
        xzfile.preset = 9
        xzfile.write("β")
        xzfile.change_block()
        xzfile.write("γ")
        xzfile.change_block()
        xzfile.write("δ")
        xzfile.change_stream()
        xzfile.write("ε")
        xzfile.change_block()
        xzfile.write("ζ")
        xzfile.change_stream()
        xzfile.write("η")
        xzfile.change_block()
        xzfile.write("θ")

    assert fileobj.getvalue() == TEST_MODE_W_PRESET_BYTES


@pytest.mark.parametrize(
    "encoding, data",
    (
        pytest.param("utf8", "еñϲоԺε", id="utf8"),
        pytest.param("latin1", "ÐµÃ±Ï²Ð¾ÔºÎµ", id="latin1"),
    ),
)
def test_mode_wt_encoding(encoding: str, data: str) -> None:
    fileobj = BytesIO()
    with xz_open(fileobj, "wt", check=0, encoding=encoding) as xzfile:
        xzfile.write(data)

    assert fileobj.getvalue() == bytes.fromhex(
        "fd377a585a000000ff12d9410200210116000000742fe5a301000bd0b5c3b1cf"
        "b2d0bed4baceb50000011c0c5da447cf06729e7a010000000000595a"
    )


@pytest.mark.parametrize(
    "errors, data",
    (
        pytest.param(None, None, id="None"),
        pytest.param("strict", None, id="strict"),
        pytest.param(
            "ignore",
            b"encoding",
            id="ignore",
        ),
        pytest.param(
            "replace",
            b"en?co?di?ng",
            id="replace",
        ),
        pytest.param(
            "backslashreplace",
            br"en\udc01co\udc02di\udc03ng",
            id="backslashreplace",
        ),
    ),
)
def test_mode_wt_encoding_errors(errors: Optional[str], data: Optional[bytes]) -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", errors=errors) as xzfile:
        if data is None:
            xzfile.write("X")  # to avoid having an empty file
            with pytest.raises(ValueError):
                xzfile.write("en\udc01co\udc0di\udc03ng")
        else:
            xzfile.write("en\udc01co\udc02di\udc03ng")

    if data is not None:
        assert lzma.decompress(fileobj.getvalue()) == data


@pytest.mark.parametrize(
    "newline, data",
    (
        pytest.param(None, b"a\nb\n", id="None"),
        pytest.param("", b"a\nb\n", id="''"),
        pytest.param("\n", b"a\nb\n", id="'\n'"),
        pytest.param("\r", b"a\rb\r", id="'\r'"),
        pytest.param("\r\n", b"a\r\nb\r\n", id="'\r\n'"),
    ),
)
def test_mode_wt_newline(newline: Optional[str], data: bytes) -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", newline=newline) as xzfile:
        xzfile.writelines(["a\n", "b\n"])

    assert lzma.decompress(fileobj.getvalue()) == data


#
# misc
#


@pytest.mark.parametrize("mode", ("rtb", "rbt", "wtb", "wbt"))
def test_mode_invalid(mode: str) -> None:
    fileobj = BytesIO(STREAM_BYTES)

    with pytest.raises(ValueError) as exc_info:
        xz_open(fileobj, mode)
    assert str(exc_info.value) == f"Invalid mode: {mode}"
