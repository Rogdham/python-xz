from io import SEEK_END, BytesIO, UnsupportedOperation
import os
from pathlib import Path
from typing import Callable, Tuple, Union, cast
from unittest.mock import Mock

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


SUPPORTED_MODES = (
    "r",
    "rb",
    "r+",
    "rb+",
    "w",
    "wb",
    "w+",
    "wb+",
    "x",
    "xb",
    "x+",
    "xb+",
)

EMPTY_XZ_FILE_WARNING_FILTER = "ignore:Empty XZFile*:RuntimeWarning:xz.file"


#
# init
#


@pytest.mark.filterwarnings(EMPTY_XZ_FILE_WARNING_FILTER)
@pytest.mark.parametrize("init_has_ability", (False, True))
@pytest.mark.parametrize("ability", ("seekable", "readable", "writable"))
@pytest.mark.parametrize("mode", SUPPORTED_MODES)
def test_required_abilities(mode: str, ability: str, init_has_ability: bool) -> None:
    fileobj = Mock(wraps=BytesIO(FILE_BYTES))
    getattr(fileobj, ability).return_value = init_has_ability

    expected_ability = (
        ability == "seekable"
        or "+" in mode
        or ((ability == "readable") == ("r" in mode))
    )

    if not init_has_ability and expected_ability:
        with pytest.raises(ValueError):
            XZFile(fileobj, mode=mode)
    else:
        with XZFile(fileobj, mode=mode) as xzfile:
            assert getattr(xzfile, ability)() == expected_ability


#
# read
#


@pytest.mark.parametrize("filetype", ("fileobj", "filename", "path"))
def test_read(
    filetype: str,
    tmp_path: Path,
    data_pattern_locate: Callable[[bytes], Tuple[int, int]],
) -> None:
    filename: Union[Path, BytesIO, str]

    if filetype == "fileobj":
        filename = BytesIO(FILE_BYTES)
    else:
        filename = tmp_path / "archive.xz"
        filename.write_bytes(FILE_BYTES)
        if filetype == "filename":
            filename = os.fspath(filename)

    with XZFile(filename) as xzfile:
        assert len(xzfile) == 400
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

        # read from pas end
        assert xzfile.seek(500) == 500
        assert xzfile.read() == b""


@pytest.mark.filterwarnings(EMPTY_XZ_FILE_WARNING_FILTER)
@pytest.mark.parametrize("from_file", (False, True))
@pytest.mark.parametrize("mode", SUPPORTED_MODES)
def test_read_with_mode(
    mode: str,
    from_file: bool,
    tmp_path: Path,
    data_pattern_locate: Callable[[bytes], Tuple[int, int]],
) -> None:
    filename: Union[Path, BytesIO]

    if from_file:
        filename = tmp_path / "archive.xz"
        filename.write_bytes(FILE_BYTES)
    else:
        filename = BytesIO(FILE_BYTES)

    if from_file and "x" in mode:
        with pytest.raises(FileExistsError):
            XZFile(filename, mode=mode)

    else:
        with XZFile(filename, mode=mode) as xzfile:
            if "r" in mode:
                assert len(xzfile) == 400
                assert data_pattern_locate(xzfile.read(20)) == (0, 20)
            elif "w" in mode or "x" in mode:
                assert len(xzfile) == 0
            else:
                with pytest.raises(UnsupportedOperation):
                    xzfile.read(20)


def test_read_invalid_stream_padding() -> None:
    filename = BytesIO(FILE_BYTES + b"\x00" * 3)

    with pytest.raises(XZError) as exc_info:
        XZFile(filename)
    assert str(exc_info.value) == "file: invalid size"


def test_read_invalid_filename_type() -> None:
    with pytest.raises(TypeError) as exc_info:
        XZFile(42)  # type: ignore[arg-type]
    assert (
        str(exc_info.value) == "filename must be a str, bytes, file or PathLike object"
    )


@pytest.mark.parametrize("data", (b"", b"\x00" * 100), ids=("empty", "only-padding"))
def test_read_no_stream(data: bytes) -> None:
    filename = BytesIO(data)

    with pytest.raises(XZError) as exc_info:
        XZFile(filename)
    assert str(exc_info.value) == "file: no streams"


#
# write
#


def test_write() -> None:
    filename = BytesIO()

    with XZFile(filename, "w") as xzfile:
        assert len(xzfile) == 0
        assert xzfile.stream_boundaries == []
        assert xzfile.block_boundaries == []

        xzfile.change_stream()  # no initial stream change
        assert len(xzfile) == 0
        assert xzfile.stream_boundaries == []
        assert xzfile.block_boundaries == []

        xzfile.change_block()  # no initial block change
        assert len(xzfile) == 0
        assert xzfile.stream_boundaries == []
        assert xzfile.block_boundaries == []

        xzfile.write(b"abc")
        assert len(xzfile) == 3
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0]

        xzfile.seek(7)
        xzfile.write(b"def")
        assert len(xzfile) == 10
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0]

        xzfile.change_block()
        assert len(xzfile) == 10
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0, 10]

        xzfile.change_block()  # no double block change
        assert len(xzfile) == 10
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0, 10]

        xzfile.write(b"ghi")
        assert len(xzfile) == 13
        assert xzfile.stream_boundaries == [0]
        assert xzfile.block_boundaries == [0, 10]

        xzfile.change_stream()
        assert len(xzfile) == 13
        assert xzfile.stream_boundaries == [0, 13]
        assert xzfile.block_boundaries == [0, 10]

        xzfile.change_stream()  # no double stream change
        assert len(xzfile) == 13
        assert xzfile.stream_boundaries == [0, 13]
        assert xzfile.block_boundaries == [0, 10]

        xzfile.write(b"jkl")
        assert len(xzfile) == 16
        assert xzfile.stream_boundaries == [0, 13]
        assert xzfile.block_boundaries == [0, 10, 13]

    assert filename.getvalue() == bytes.fromhex(
        # stream 1
        "fd377a585a000004e6d6b4460200210116000000742fe5a30100096162630000"
        "0000646566000000b8179b68f9f2cff30200210116000000742fe5a301000267"
        "686900005d4f3084613135140002220a1b0300001b1c3777b1c467fb02000000"
        "0004595a"
        # stream 2
        "fd377a585a000004e6d6b4460200210116000000742fe5a30100026a6b6c0000"
        "2cf7f76df2f5538800011b030b2fb9101fb6f37d010000000004595a"
    )


@pytest.mark.parametrize(
    "mode, start_empty",
    [
        (mode, start_empty)
        for mode in SUPPORTED_MODES
        if not mode[0] == "r"
        for start_empty in ((True,) if mode[0] == "a" else (False, True))
    ],
)
def test_write_empty(mode: str, start_empty: bool) -> None:
    filename = BytesIO(b"" if start_empty else FILE_BYTES)

    with pytest.warns(RuntimeWarning):
        with XZFile(filename, mode=mode):
            pass

    assert filename.getvalue() == b""


@pytest.mark.parametrize("file_exists", (False, True))
@pytest.mark.parametrize("from_file", (False, True))
@pytest.mark.parametrize("mode", SUPPORTED_MODES)
def test_write_with_mode(
    mode: str, from_file: bool, file_exists: bool, tmp_path: Path
) -> None:
    initial_data = bytes.fromhex(
        "fd377a585a000004e6d6b446"  # header
        "0200210116000000742fe5a301000278797a0000f5e0ef978aa11258"  # block
        "00011b030b2fb910"  # index
        "1fb6f37d010000000004595a"  # footer
    )

    filename: Union[Path, BytesIO]

    if from_file:
        filename = tmp_path / "archive.xz"
        if file_exists:
            filename.write_bytes(initial_data)
    else:
        if file_exists:
            filename = BytesIO(initial_data)
        else:
            filename = BytesIO()

    if not file_exists and "r" in mode:
        if from_file:
            with pytest.raises(FileNotFoundError):
                XZFile(filename, mode=mode)

        else:
            with pytest.raises(XZError) as exc_info:
                XZFile(filename, mode=mode)
            assert str(exc_info.value) == "file: no streams"

    elif from_file and file_exists and "x" in mode:
        with pytest.raises(FileExistsError):
            XZFile(filename, mode=mode)

    else:
        expected_success = "r" not in mode or "+" in mode

        with XZFile(filename, mode=mode) as xzfile:
            assert xzfile.tell() == 0
            if "r" in mode:
                xzfile.seek(0, SEEK_END)

            if expected_success:
                xzfile.write(b"abc")
            else:
                with pytest.raises(UnsupportedOperation):
                    xzfile.write(b"abc")

        if expected_success:
            if from_file:
                value = cast(Path, filename).read_bytes()
            else:
                value = cast(BytesIO, filename).getvalue()
            if "r" in mode:
                expected_value = bytes.fromhex(
                    "fd377a585a000004e6d6b446"  # header
                    "0200210116000000742fe5a301000278797a0000f5e0ef978aa11258"  # old block
                    "0200210116000000742fe5a301000261626300002776271a4a09d82c"  # new block
                    "00021b031b0300000f285259"  # index
                    "b1c467fb020000000004595a"  # footer
                )
            else:
                expected_value = bytes.fromhex(
                    "fd377a585a000004e6d6b446"  # header
                    "0200210116000000742fe5a301000261626300002776271a4a09d82c"  # new block
                    "00011b030b2fb910"  # index
                    "1fb6f37d010000000004595a"  # footer
                )
            assert value == expected_value


#
# check / filters / preset changes
#


def test_change_check() -> None:
    fileobj = BytesIO()

    with XZFile(fileobj, "w", check=1) as xzfile:
        xzfile.write(b"aa")
        xzfile.change_stream()
        xzfile.check = 4
        xzfile.write(b"bb")
        xzfile.change_stream()
        xzfile.write(b"cc")
        xzfile.change_stream()
        xzfile.write(b"dd")

    assert fileobj.getvalue() == bytes.fromhex(
        # stream 1
        "fd377a585a0000016922de36"
        "0200210116000000742fe5a30100016161000000d7198a07"
        "00011602d06110d2"
        "9042990d010000000001595a"
        # stream 2
        "fd377a585a0000016922de36"
        "0200210116000000742fe5a30100016262000000ae1baeb5"
        "00011602d06110d2"
        "9042990d010000000001595a"
        # stream 3 (changed check)
        "fd377a585a000004e6d6b446"
        "0200210116000000742fe5a30100016363000000330d82b4bacc99a6"
        "00011a02dc2ea57e"
        "1fb6f37d010000000004595a"
        # stream 4 (changed check)
        "fd377a585a000004e6d6b446"
        "0200210116000000742fe5a301000164640000009265d6d903b6a5a6"
        "00011a02dc2ea57e"
        "1fb6f37d010000000004595a"
    )


def test_change_check_on_existing() -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            # stream 1
            "fd377a585a0000016922de36"
            "0200210116000000742fe5a30100016161000000d7198a07"
            "00011602d06110d2"
            "9042990d010000000001595a"
        )
    )

    with XZFile(fileobj, "r+", check=4) as xzfile:
        xzfile.seek(0, SEEK_END)
        xzfile.write(b"bb")
        xzfile.change_stream()
        xzfile.write(b"cc")

    assert fileobj.getvalue() == bytes.fromhex(
        # stream 1
        "fd377a585a0000016922de36"
        "0200210116000000742fe5a30100016161000000d7198a07"  # existing
        "0200210116000000742fe5a30100016262000000ae1baeb5"  # same check
        "00021602160200008ba0042b"
        "3e300d8b020000000001595a"
        # stream 2 (changed check)
        "fd377a585a000004e6d6b446"
        "0200210116000000742fe5a30100016363000000330d82b4bacc99a6"
        "00011a02dc2ea57e"
        "1fb6f37d010000000004595a"
    )


def test_change_filters() -> None:
    fileobj = BytesIO()

    with XZFile(fileobj, "w", check=1) as xzfile:
        xzfile.write(b"aa")
        xzfile.change_block()
        xzfile.filters = [{"id": 3, "dist": 1}, {"id": 33}]
        xzfile.write(b"bb")
        xzfile.change_block()
        xzfile.write(b"cc")
        xzfile.change_block()
        xzfile.write(b"dd")
        xzfile.change_stream()
        xzfile.write(b"ee")
        xzfile.change_block()
        xzfile.write(b"ff")
        xzfile.change_stream()
        xzfile.write(b"gg")
        xzfile.change_block()
        xzfile.write(b"hh")

    assert fileobj.getvalue() == bytes.fromhex(
        ## stream 1
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
        ## stream 2
        # header
        "fd377a585a0000016922de36"
        # block 1 (changed filters)
        "02010301002101167920c4ee0100016500000000ca188b64"
        # block 2 (changed filters)
        "02010301002101167920c4ee0100016600000000b31aafd6"
        # index
        "00021602160200008ba0042b"
        # footer
        "3e300d8b020000000001595a"
        ## stream 3
        # header
        "fd377a585a0000016922de36"
        # block 1 (changed filters)
        "02010301002101167920c4ee0100016700000000641bb3b8"
        # block 2 (changed filters)
        "02010301002101167920c4ee01000168000000003a1a94af"
        # index
        "00021602160200008ba0042b"
        # footer
        "3e300d8b020000000001595a"
    )


def test_change_filters_on_existing() -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            # stream 1
            "fd377a585a0000016922de36"
            "0200210116000000742fe5a30100016161000000d7198a07"
            "00011602d06110d2"
            "9042990d010000000001595a"
        )
    )

    with XZFile(fileobj, "r+", filters=[{"id": 3, "dist": 1}, {"id": 33}]) as xzfile:
        xzfile.seek(0, SEEK_END)
        xzfile.write(b"bb")
        xzfile.change_block()
        xzfile.write(b"cc")

    assert fileobj.getvalue() == bytes.fromhex(
        "fd377a585a0000016922de36"
        "0200210116000000742fe5a30100016161000000d7198a07"  # existing
        "02010301002101167920c4ee0100016200000000ae1baeb5"  # new filters
        "02010301002101167920c4ee0100016300000000791ab2db"  # new filters
        "0003160216021602c47fe57f"
        "3e300d8b020000000001595a"
    )


def test_change_preset() -> None:
    fileobj = BytesIO()

    with XZFile(fileobj, "w", check=1) as xzfile:
        xzfile.write(b"aa")
        xzfile.change_block()
        xzfile.preset = 9
        xzfile.write(b"bb")
        xzfile.change_block()
        xzfile.write(b"cc")
        xzfile.change_block()
        xzfile.write(b"dd")
        xzfile.change_stream()
        xzfile.write(b"ee")
        xzfile.change_block()
        xzfile.write(b"ff")
        xzfile.change_stream()
        xzfile.write(b"gg")
        xzfile.change_block()
        xzfile.write(b"hh")

    assert fileobj.getvalue() == bytes.fromhex(
        ## stream 1
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
        ## stream 2
        # header
        "fd377a585a0000016922de36"
        # block 1 (changed preset)
        "020021011c00000010cf58cc0100016565000000ca188b64"
        # block 2 (changed preset)
        "020021011c00000010cf58cc0100016666000000b31aafd6"
        # index
        "00021602160200008ba0042b"
        # footer
        "3e300d8b020000000001595a"
        ## stream 3
        # header
        "fd377a585a0000016922de36"
        # block 1 (changed preset)
        "020021011c00000010cf58cc0100016767000000641bb3b8"
        # block 2 (changed preset)
        "020021011c00000010cf58cc01000168680000003a1a94af"
        # index
        "00021602160200008ba0042b"
        # footer
        "3e300d8b020000000001595a"
    )


def test_change_preset_on_existing() -> None:
    fileobj = BytesIO(
        bytes.fromhex(
            # stream 1
            "fd377a585a0000016922de36"
            "0200210116000000742fe5a30100016161000000d7198a07"
            "00011602d06110d2"
            "9042990d010000000001595a"
        )
    )

    with XZFile(fileobj, "r+", preset=9) as xzfile:
        xzfile.seek(0, SEEK_END)
        xzfile.write(b"bb")
        xzfile.change_block()
        xzfile.write(b"cc")

    assert fileobj.getvalue() == bytes.fromhex(
        "fd377a585a0000016922de36"
        "0200210116000000742fe5a30100016161000000d7198a07"  # existing
        "020021011c00000010cf58cc0100016262000000ae1baeb5"  # new preset
        "020021011c00000010cf58cc0100016363000000791ab2db"  # new preset
        "0003160216021602c47fe57f"
        "3e300d8b020000000001595a"
    )


#
# misc
#


@pytest.mark.parametrize(
    "mode",
    (
        "rt",
        "r+t",
        "wt",
        "w+t",
        "xt",
        "x+t",
        "at",
        "a+t",
        "rw",
        "rw+",
        "rwb",
        "rw+b",
        "rwt",
        "rw+t",
        "rx",
        "rx+",
        "rxb",
        "rx+b",
        "rxt",
        "rx+t",
        "what-is-this",
    ),
)
def test_invalid_mode(mode: str) -> None:
    filename = BytesIO(FILE_BYTES)
    with pytest.raises(ValueError) as exc_info:
        XZFile(filename, mode)
    assert str(exc_info.value) == f"invalid mode: {mode}"


def test_fileno(tmp_path: Path) -> None:
    file_path = tmp_path / "file.xz"
    file_path.write_bytes(FILE_BYTES)

    with file_path.open("rb") as fin:
        with XZFile(fin) as xzfile:
            assert xzfile.fileno() == fin.fileno()


def test_fileno_error(tmp_path: Path) -> None:
    file_path = tmp_path / "file.xz"
    file_path.write_bytes(FILE_BYTES)

    with file_path.open("rb") as fin:
        mock = Mock(wraps=fin)
        mock.fileno.side_effect = AttributeError()
        with XZFile(mock) as xzfile:
            with pytest.raises(UnsupportedOperation):
                xzfile.fileno()
