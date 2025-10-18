from io import BytesIO
import lzma
from pathlib import Path
from unittest.mock import Mock

import pytest

from xz.open import xz_open
from xz.strategy import RollingBlockReadStrategy

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
        assert xzfile.mode == "r"
        assert len(xzfile) == 13
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0, 10]

        assert xzfile.read() == b"\xe2\x99\xa5 utf8 \xe2\x99\xa5\n"

        assert xzfile.seek(9) == 9
        assert xzfile.read() == b"\xe2\x99\xa5\n"


def test_mode_rt() -> None:
    fileobj = BytesIO(STREAM_BYTES)

    with xz_open(fileobj, "rt") as xzfile:
        assert xzfile.mode == "rt"
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0, 10]

        assert xzfile.read() == "♥ utf8 ♥\n"

        assert xzfile.seek(9) == 9
        assert xzfile.read() == "♥\n"


def test_mode_rt_file(tmp_path: Path) -> None:
    file_path = tmp_path / "file.xz"
    file_path.write_bytes(STREAM_BYTES)

    with file_path.open("rb") as fin, xz_open(fin, "rt") as xzfile:
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0, 10]
        assert xzfile.fileno() == fin.fileno()

        assert xzfile.read() == "♥ utf8 ♥\n"

        assert xzfile.seek(9) == 9
        assert xzfile.read() == "♥\n"


@pytest.mark.parametrize(
    ["encoding", "expected"],
    [
        pytest.param("utf8", "еñϲоԺε", id="utf8"),
        pytest.param("latin1", "ÐµÃ±Ï²Ð¾ÔºÎµ", id="latin1"),
    ],
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
    ["errors", "expected"],
    [
        pytest.param(None, None, id="None"),
        pytest.param("strict", None, id="strict"),
        pytest.param("ignore", "encoding", id="ignore"),
        pytest.param("replace", "en�co�di�ng", id="replace"),
        pytest.param(
            "backslashreplace", r"en\x99co\x98di\x97ng", id="backslashreplace"
        ),
    ],
)
def test_mode_rt_encoding_errors(errors: str | None, expected: str | None) -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000000ff12d9410200210116000000742fe5a301000a656e99636f"
            "986469976e67000000011b0b39a7621e06729e7a010000000000595a"
        )
    )

    with xz_open(fileobj, "rt", errors=errors) as xzfile:
        if expected is None:
            with pytest.raises(UnicodeDecodeError):
                xzfile.read()
        else:
            assert xzfile.read() == expected


@pytest.mark.parametrize(
    ["newline", "expected"],
    [
        pytest.param(None, ["a\n", "b\n", "c\n", "d"], id="None"),
        pytest.param("", ["a\n", "b\r", "c\r\n", "d"], id="''"),
        pytest.param("\n", ["a\n", "b\rc\r\n", "d"], id="'\n'"),
        pytest.param("\r", ["a\nb\r", "c\r", "\nd"], id="'\r'"),
        pytest.param("\r\n", ["a\nb\rc\r\n", "d"], id="'\r\n'"),
    ],
)
def test_mode_rt_newline(newline: str | None, expected: list[str]) -> None:
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
    with pytest.raises(
        ValueError, match=r"^Argument 'encoding' not supported in binary mode$"
    ):
        xz_open(fileobj, "rb", encoding="latin1")


def test_mode_rb_encoding_errors() -> None:
    fileobj = BytesIO(STREAM_BYTES)
    with pytest.raises(
        ValueError, match=r"^Argument 'errors' not supported in binary mode$"
    ):
        xz_open(fileobj, "rb", errors="ignore")


def test_mode_rb_newline() -> None:
    fileobj = BytesIO(STREAM_BYTES)
    with pytest.raises(
        ValueError, match=r"^Argument 'newline' not supported in binary mode$"
    ):
        xz_open(fileobj, "rb", newline="\n")


#
# write
#

TEST_MODE_W_CHECK_BYTES = bytes.fromhex(
    # stream 1
    "fd377a585a0000016922de36"
    "0200210116000000742fe5a3010001d4b1000000fe91eb18"
    "00011602d06110d2"
    "9042990d010000000001595a"
    # stream 2
    "fd377a585a0000016922de36"
    "0200210116000000742fe5a3010001d4b200000044c0e281"
    "00011602d06110d2"
    "9042990d010000000001595a"
    # stream 3 (changed check)
    "fd377a585a000004e6d6b446"
    "0200210116000000742fe5a3010001d4b30000009872e047a72fa9ba"
    "00011a02dc2ea57e"
    "1fb6f37d010000000004595a"
    # stream 4 (changed check)
    "fd377a585a000004e6d6b446"
    "0200210116000000742fe5a3010001d4b40000009fd38813ca96d386"
    "00011a02dc2ea57e"
    "1fb6f37d010000000004595a"
)


def test_mode_wb_check() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wb", check=1) as xzfile:
        assert xzfile.mode == "w"
        xzfile.write(b"\xd4\xb1")
        xzfile.change_stream()
        xzfile.check = 4
        xzfile.write(b"\xd4\xb2")
        xzfile.change_stream()
        xzfile.write(b"\xd4\xb3")
        xzfile.change_stream()
        xzfile.write(b"\xd4\xb4")

    assert fileobj.getvalue() == TEST_MODE_W_CHECK_BYTES


def test_mode_wt_check() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", check=1) as xzfile:
        assert xzfile.mode == "wt"
        xzfile.write("Ա")
        xzfile.change_stream()
        xzfile.check = 4
        xzfile.write("Բ")
        xzfile.change_stream()
        xzfile.write("Գ")
        xzfile.change_stream()
        xzfile.write("Դ")

    assert fileobj.getvalue() == TEST_MODE_W_CHECK_BYTES


TEST_MODE_W_FILTERS_BYTES = bytes.fromhex(
    ## stream 1
    # header
    "fd377a585a0000016922de36"
    # block 1
    "0200210116000000742fe5a3010001d4b1000000fe91eb18"
    # block 2
    "0200210116000000742fe5a3010001d4b200000044c0e281"
    # block 3 (changed filters)
    "02010301002101167920c4ee010001d4df000000d2f0e5f6"
    # block 4 (changed filters)
    "02010301002101167920c4ee010001d4e000000071658168"
    # index
    "0004160216021602160200008a2bb83b"
    # footer
    "9be35140030000000001595a"
    ## stream 2
    # header
    "fd377a585a0000016922de36"
    # block 1 (changed filters)
    "02010301002101167920c4ee010001d4e1000000e755861f"
    # block 2 (changed filters)
    "02010301002101167920c4ee010001d4e20000005d048f86"
    # index
    "00021602160200008ba0042b"
    # footer
    "3e300d8b020000000001595a"
    ## stream 3
    # header
    "fd377a585a0000016922de36"
    # block 1 (changed filters)
    "02010301002101167920c4ee010001d4e3000000cb3488f1"
    # block 2 (changed filters)
    "02010301002101167920c4ee010001d4e40000005a293761"
    # index
    "00021602160200008ba0042b"
    # footer
    "3e300d8b020000000001595a"
)


def test_mode_wb_filters() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wb", check=1) as xzfile:
        xzfile.write(b"\xd4\xb1")
        xzfile.change_block()
        xzfile.filters = [{"id": 3, "dist": 1}, {"id": 33}]
        xzfile.write(b"\xd4\xb2")
        xzfile.change_block()
        xzfile.write(b"\xd4\xb3")
        xzfile.change_block()
        xzfile.write(b"\xd4\xb4")
        xzfile.change_stream()
        xzfile.write(b"\xd4\xb5")
        xzfile.change_block()
        xzfile.write(b"\xd4\xb6")
        xzfile.change_stream()
        xzfile.write(b"\xd4\xb7")
        xzfile.change_block()
        xzfile.write(b"\xd4\xb8")

    assert fileobj.getvalue() == TEST_MODE_W_FILTERS_BYTES


def test_mode_wt_filters() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", check=1) as xzfile:
        xzfile.write("Ա")
        xzfile.change_block()
        xzfile.filters = [{"id": 3, "dist": 1}, {"id": 33}]
        xzfile.write("Բ")
        xzfile.change_block()
        xzfile.write("Գ")
        xzfile.change_block()
        xzfile.write("Դ")
        xzfile.change_stream()
        xzfile.write("Ե")
        xzfile.change_block()
        xzfile.write("Զ")
        xzfile.change_stream()
        xzfile.write("Է")
        xzfile.change_block()
        xzfile.write("Ը")

    assert fileobj.getvalue() == TEST_MODE_W_FILTERS_BYTES


TEST_MODE_W_PRESET_BYTES = bytes.fromhex(
    ## stream 1
    # header
    "fd377a585a0000016922de36"
    # block 1
    "0200210116000000742fe5a3010001d4b1000000fe91eb18"
    # block 2
    "0200210116000000742fe5a3010001d4b200000044c0e281"
    # block 3 (changed preset)
    "020021011c00000010cf58cc010001d4b3000000d2f0e5f6"
    # block 4 (changed preset)
    "020021011c00000010cf58cc010001d4b400000071658168"
    # index
    "0004160216021602160200008a2bb83b"
    # footer
    "9be35140030000000001595a"
    ## stream 2
    # header
    "fd377a585a0000016922de36"
    # block 1 (changed preset)
    "020021011c00000010cf58cc010001d4b5000000e755861f"
    # block 2 (changed preset)
    "020021011c00000010cf58cc010001d4b60000005d048f86"
    # index
    "00021602160200008ba0042b"
    # footer
    "3e300d8b020000000001595a"
    ## stream 3
    # header
    "fd377a585a0000016922de36"
    # block 1 (changed preset)
    "020021011c00000010cf58cc010001d4b7000000cb3488f1"
    # block 2 (changed preset)
    "020021011c00000010cf58cc010001d4b80000005a293761"
    # index
    "00021602160200008ba0042b"
    # footer
    "3e300d8b020000000001595a"
)


def test_mode_wb_preset() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wb", check=1) as xzfile:
        xzfile.write(b"\xd4\xb1")
        xzfile.change_block()
        xzfile.preset = 9
        xzfile.write(b"\xd4\xb2")
        xzfile.change_block()
        xzfile.write(b"\xd4\xb3")
        xzfile.change_block()
        xzfile.write(b"\xd4\xb4")
        xzfile.change_stream()
        xzfile.write(b"\xd4\xb5")
        xzfile.change_block()
        xzfile.write(b"\xd4\xb6")
        xzfile.change_stream()
        xzfile.write(b"\xd4\xb7")
        xzfile.change_block()
        xzfile.write(b"\xd4\xb8")

    assert fileobj.getvalue() == TEST_MODE_W_PRESET_BYTES


def test_mode_wt_preset() -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", check=1) as xzfile:
        xzfile.write("Ա")
        xzfile.change_block()
        xzfile.preset = 9
        xzfile.write("Բ")
        xzfile.change_block()
        xzfile.write("Գ")
        xzfile.change_block()
        xzfile.write("Դ")
        xzfile.change_stream()
        xzfile.write("Ե")
        xzfile.change_block()
        xzfile.write("Զ")
        xzfile.change_stream()
        xzfile.write("Է")
        xzfile.change_block()
        xzfile.write("Ը")

    assert fileobj.getvalue() == TEST_MODE_W_PRESET_BYTES


@pytest.mark.parametrize(
    ["encoding", "data"],
    [
        pytest.param("utf8", "еñϲоԺε", id="utf8"),
        pytest.param("latin1", "ÐµÃ±Ï²Ð¾ÔºÎµ", id="latin1"),
    ],
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
    ["errors", "data"],
    [
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
            rb"en\udc01co\udc02di\udc03ng",
            id="backslashreplace",
        ),
    ],
)
def test_mode_wt_encoding_errors(errors: str | None, data: bytes | None) -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", errors=errors) as xzfile:
        if data is None:
            xzfile.write("X")  # to avoid having an empty file
            with pytest.raises(UnicodeError):
                xzfile.write("en\udc01co\udc0di\udc03ng")
        else:
            xzfile.write("en\udc01co\udc02di\udc03ng")

    if data is not None:
        assert lzma.decompress(fileobj.getvalue()) == data


@pytest.mark.parametrize(
    ["newline", "data"],
    [
        pytest.param(None, b"a\nb\n", id="None"),
        pytest.param("", b"a\nb\n", id="''"),
        pytest.param("\n", b"a\nb\n", id="'\n'"),
        pytest.param("\r", b"a\rb\r", id="'\r'"),
        pytest.param("\r\n", b"a\r\nb\r\n", id="'\r\n'"),
    ],
)
def test_mode_wt_newline(newline: str | None, data: bytes) -> None:
    fileobj = BytesIO()

    with xz_open(fileobj, "wt", newline=newline) as xzfile:
        xzfile.writelines(["a\n", "b\n"])

    assert lzma.decompress(fileobj.getvalue()) == data


#
# misc
#


@pytest.mark.parametrize("mode", ["rtb", "rbt", "wtb", "wbt"])
def test_mode_invalid(mode: str) -> None:
    fileobj = BytesIO(STREAM_BYTES)

    with pytest.raises(ValueError, match=r"^Invalid mode: "):
        xz_open(fileobj, mode)


@pytest.mark.parametrize("mode", ["r", "rt"])
def test_default_strategy(mode: str) -> None:
    fileobj = BytesIO(STREAM_BYTES)

    with xz_open(fileobj, mode) as xzfile:
        assert isinstance(xzfile.block_read_strategy, RollingBlockReadStrategy)


@pytest.mark.parametrize("mode", ["r", "rt"])
def test_custom_strategy(mode: str) -> None:
    fileobj = BytesIO(STREAM_BYTES)
    strategy = Mock()

    with xz_open(fileobj, mode, block_read_strategy=strategy) as xzfile:
        assert xzfile.block_read_strategy == strategy
