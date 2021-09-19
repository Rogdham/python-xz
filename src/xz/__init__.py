try:
    from xz._version import __version__
except ImportError:  # pragma: no cover
    __version__ = "0.0.0.dev0-unknown"

from xz.common import XZError
from xz.file import XZFile
from xz.open import xz_open

# pylint: disable=redefined-builtin
open = xz_open
# pylint: enable=redefined-builtin


__all__ = (
    "__version__",
    "XZError",
    "XZFile",
    "open",
)
