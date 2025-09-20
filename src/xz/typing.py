from collections.abc import Mapping, Sequence
from os import PathLike
from typing import TYPE_CHECKING, Any, BinaryIO, Literal, Optional, Protocol, Union

_LZMAFilenameType = Union[str, bytes, PathLike[str], PathLike[bytes], BinaryIO]


if TYPE_CHECKING:  # pragma: no cover
    # avoid circular dependency
    from xz.block import XZBlock


_LZMAPresetType = Optional[int]
_LZMAFiltersType = Optional[Sequence[Mapping[str, Any]]]


# all valid modes if we don't consider changing order nor repetitions
# (see utils.parse_mode for more details)
# the values are unit tested in test_parse_mode to make sure that all are here
_XZModesBinaryType = Literal[
    "r", "r+", "w", "w+", "x", "x+", "rb", "rb+", "wb", "wb+", "xb", "xb+"
]
_XZModesTextType = Literal["rt", "rt+", "wt", "wt+", "xt", "xt+"]


class _BlockReadStrategyType(Protocol):  # noqa: PYI046
    def on_create(self, block: "XZBlock") -> None: ...  # pragma: no cover

    def on_delete(self, block: "XZBlock") -> None: ...  # pragma: no cover

    def on_read(self, block: "XZBlock") -> None: ...  # pragma: no cover
