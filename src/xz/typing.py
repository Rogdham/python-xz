from os import PathLike
import sys
from typing import TYPE_CHECKING, Any, BinaryIO, Mapping, Optional, Sequence, Union

if sys.version_info >= (3, 9):  # pragma: no cover
    _LZMAFilenameType = Union[str, bytes, PathLike[str], PathLike[bytes], BinaryIO]
    from typing import Literal
else:  # pragma: no cover
    _LZMAFilenameType = Union[str, bytes, PathLike, BinaryIO]

    # ducktype Literal (NB we cannot use __class_getitem__ on Python 3.6)
    # we could require typing-extensions package but that's hardly an improvement

    class LiteralKlass:
        def __getitem__(self, items: Any) -> str:
            return f"Literal{list(items)}"

    Literal = LiteralKlass()


if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import Protocol
else:  # pragma: no cover
    # ducktype Protocol
    # we could require typing-extensions package instead
    Protocol = object

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
