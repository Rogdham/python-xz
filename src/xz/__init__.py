from xz.common import XZError
from xz.file import XZFile
from xz.open import xz_open

# pylint: disable=redefined-builtin
open = xz_open
# pylint: enable=redefined-builtin


__all__ = (
    "XZError",
    "XZFile",
    "open",
)
