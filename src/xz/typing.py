from os import PathLike
import sys
from typing import TYPE_CHECKING, Any, BinaryIO, Optional, Union

if sys.version_info >= (3, 9):  # pragma: no cover
    from collections.abc import Mapping, Sequence

    _LZMAFilenameType = Union[str, bytes, PathLike[str], PathLike[bytes], BinaryIO]
else:  # pragma: no cover
    from typing import Mapping, Sequence

    _LZMAFilenameType = Union[str, bytes, PathLike, BinaryIO]


if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Literal, Protocol
else:  # pragma: no cover
    from typing_extensions import Literal, Protocol


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


class _BlockReadStrategyType(Protocol):
    def on_create(self, block: "XZBlock") -> None:
        ...  # pragma: no cover

    def on_delete(self, block: "XZBlock") -> None:
        ...  # pragma: no cover

    def on_read(self, block: "XZBlock") -> None:
        ...  # pragma: no cover
