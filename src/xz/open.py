from functools import wraps
from io import TextIOWrapper
from typing import BinaryIO, List, Optional, Union, cast, overload

from xz.file import XZFile
from xz.typing import (
    _BlockReadStrategyType,
    _LZMAFilenameType,
    _LZMAFiltersType,
    _LZMAPresetType,
    _XZModesBinaryType,
    _XZModesTextType,
)
from xz.utils import AttrProxy


class _XZFileText(TextIOWrapper):
    def __init__(
        self,
        filename: _LZMAFilenameType,
        mode: str,
        *,
        check: int = -1,
        preset: _LZMAPresetType = None,
        filters: _LZMAFiltersType = None,
        block_read_strategy: Optional[_BlockReadStrategyType] = None,
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        newline: Optional[str] = None,
    ) -> None:
        self.xz_file = XZFile(
            filename,
            mode.replace("t", ""),
            check=check,
            preset=preset,
            filters=filters,
            block_read_strategy=block_read_strategy,
        )
        super().__init__(
            cast(BinaryIO, self.xz_file),
            encoding,
            errors,
            newline,
        )

    check = AttrProxy[int]("xz_file")
    preset = AttrProxy[_LZMAPresetType]("xz_file")
    filters = AttrProxy[_LZMAFiltersType]("xz_file")
    stream_boundaries = AttrProxy[List[int]]("xz_file")
    block_boundaries = AttrProxy[List[int]]("xz_file")
    block_read_strategy = AttrProxy[_BlockReadStrategyType]("xz_file")

    @property
    def mode(self) -> str:
        return f"{self.xz_file.mode}t"

    @wraps(XZFile.change_stream)
    def change_stream(self) -> None:
        self.flush()
        self.xz_file.change_stream()

    @wraps(XZFile.change_block)
    def change_block(self) -> None:
        self.flush()
        self.xz_file.change_block()


@overload
def xz_open(
    filename: _LZMAFilenameType,
    mode: _XZModesBinaryType = "rb",
    *,
    # XZFile kwargs
    check: int = -1,
    preset: _LZMAPresetType = None,
    filters: _LZMAFiltersType = None,
    block_read_strategy: Optional[_BlockReadStrategyType] = None,
    # text-mode kwargs
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
) -> XZFile:
    ...  # pragma: no cover


@overload
def xz_open(
    filename: _LZMAFilenameType,
    mode: _XZModesTextType,
    *,
    # XZFile kwargs
    check: int = -1,
    preset: _LZMAPresetType = None,
    filters: _LZMAFiltersType = None,
    block_read_strategy: Optional[_BlockReadStrategyType] = None,
    # text-mode kwargs
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
) -> _XZFileText:
    ...  # pragma: no cover


@overload
def xz_open(
    filename: _LZMAFilenameType,
    mode: str,
    *,
    # XZFile kwargs
    check: int = -1,
    preset: _LZMAPresetType = None,
    filters: _LZMAFiltersType = None,
    block_read_strategy: Optional[_BlockReadStrategyType] = None,
    # text-mode kwargs
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
) -> Union[XZFile, _XZFileText]:
    ...  # pragma: no cover


def xz_open(
    filename: _LZMAFilenameType,
    mode: str = "rb",
    *,
    # XZFile kwargs
    check: int = -1,
    preset: _LZMAPresetType = None,
    filters: _LZMAFiltersType = None,
    block_read_strategy: Optional[_BlockReadStrategyType] = None,
    # text-mode kwargs
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
) -> Union[XZFile, _XZFileText]:
    """Open an XZ file in binary or text mode.

    filename can be either an actual file name (given as a str, bytes,
    or PathLike object), in which case the named file is opened, or it
    can be an existing file object to read from or write to.

    For binary mode, this function is equivalent to the XZFile
    constructor: XZFile(filename, mode, ...). In this case, the
    encoding, errors and newline arguments must not be provided.

    For text mode, an XZFile object is created, and wrapped in an
    io.TextIOWrapper instance with the specified encoding, error
    handling behavior, and line ending(s).
    """
    if "t" in mode:
        if "b" in mode:
            raise ValueError(f"Invalid mode: {mode}")

        return _XZFileText(
            filename,
            mode,
            check=check,
            preset=preset,
            filters=filters,
            block_read_strategy=block_read_strategy,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    if encoding is not None:
        raise ValueError("Argument 'encoding' not supported in binary mode")
    if errors is not None:
        raise ValueError("Argument 'errors' not supported in binary mode")
    if newline is not None:
        raise ValueError("Argument 'newline' not supported in binary mode")

    return XZFile(
        filename,
        mode,
        check=check,
        preset=preset,
        filters=filters,
        block_read_strategy=block_read_strategy,
    )
