from io import BytesIO

import pytest

from xz.open import xz_open

# a stream with two blocks (lengths: 10, 3)
STREAM_BYTES = bytes.fromhex(
    "fd377a585a000004e6d6b4460200210116000000742fe5a3010009e299a52075"
    "74663820e2000000404506004bafe33d0200210116000000742fe5a301000299"
    "a50a0000c6687a2b8dbda0cf0002220a1b0300001b1c3777b1c467fb02000000"
    "0004595a"
)


def test_open_rb():
    fileobj = BytesIO(STREAM_BYTES)

    with xz_open(fileobj, "rb") as xz_file:
        assert xz_file._length == 13  # pylint: disable=protected-access
        assert xz_file.stream_boundaries == [0]
        assert xz_file.block_boundaries == [0, 10]

        assert xz_file.read() == b"\xe2\x99\xa5 utf8 \xe2\x99\xa5\n"

        assert xz_file.seek(9) == 9
        assert xz_file.read() == b"\xe2\x99\xa5\n"


def test_open_rt():
    fileobj = BytesIO(STREAM_BYTES)

    with xz_open(fileobj, "rt") as xz_file:
        assert xz_file.stream_boundaries == [0]
        assert xz_file.block_boundaries == [0, 10]

        assert xz_file.read() == "♥ utf8 ♥\n"

        assert xz_file.seek(9) == 9
        assert xz_file.read() == "♥\n"


@pytest.mark.parametrize("mode", ("rtb", "rbt"))
def test_open_mode_invalid(mode):
    fileobj = BytesIO(STREAM_BYTES)

    with pytest.raises(ValueError) as exc_info:
        xz_open(fileobj, mode)
    assert str(exc_info.value) == f"Invalid mode: {mode}"


@pytest.mark.parametrize(
    "encoding, expected",
    (
        pytest.param("utf8", "еñϲоԺε", id="utf8"),
        pytest.param("latin1", "ÐµÃ±Ï²Ð¾ÔºÎµ", id="latin1"),
    ),
)
def test_open_encoding(encoding, expected):
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000000ff12d9410200210116000000742fe5a301000bd0b5c3b1cf"
            "b2d0bed4baceb50000011c0c5da447cf06729e7a010000000000595a"
        )
    )
    with xz_open(fileobj, "rt", encoding=encoding) as xz_file:
        assert xz_file.read() == expected


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
def test_open_encoding_errors(errors, expected):
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000000ff12d9410200210116000000742fe5a301000a656e99636f"
            "986469976e67000000011b0b39a7621e06729e7a010000000000595a"
        )
    )

    with xz_open(fileobj, "rt", errors=errors) as xz_file:
        if expected is None:
            with pytest.raises(ValueError):
                xz_file.read()
        else:
            assert xz_file.read() == expected


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
def test_open_newline(newline, expected):
    fileobj = BytesIO(
        bytes.fromhex(
            "fd377a585a000000ff12d9410200210116000000742fe5a3010007610a620d63"
            "0d0a64000001180840a546ac06729e7a010000000000595a"
        )
    )

    with xz_open(fileobj, "rt", newline=newline) as xz_file:
        assert xz_file.readlines() == expected


def test_open_binary_encoding():
    fileobj = BytesIO(STREAM_BYTES)
    with pytest.raises(ValueError):
        xz_open(fileobj, "rb", encoding="latin1")


def test_open_binary_encoding_errors():
    fileobj = BytesIO(STREAM_BYTES)
    with pytest.raises(ValueError):
        xz_open(fileobj, "rb", errors="ignore")


def test_open_binary_newline():
    fileobj = BytesIO(STREAM_BYTES)
    with pytest.raises(ValueError):
        xz_open(fileobj, "rb", newline="\n")
