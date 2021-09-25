from lzma import (
    CHECK_CRC32,
    CHECK_CRC64,
    CHECK_ID_MAX,
    CHECK_NONE,
    CHECK_SHA256,
    CHECK_UNKNOWN,
    FILTER_ARM,
    FILTER_ARMTHUMB,
    FILTER_DELTA,
    FILTER_IA64,
    FILTER_LZMA1,
    FILTER_LZMA2,
    FILTER_POWERPC,
    FILTER_SPARC,
    FILTER_X86,
    MF_BT2,
    MF_BT3,
    MF_BT4,
    MF_HC3,
    MF_HC4,
    MODE_FAST,
    MODE_NORMAL,
    PRESET_DEFAULT,
    PRESET_EXTREME,
    compress,
    decompress,
    is_check_supported,
)

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
    # re-export from lzma for easy access
    "CHECK_CRC32",
    "CHECK_CRC64",
    "CHECK_ID_MAX",
    "CHECK_NONE",
    "CHECK_SHA256",
    "CHECK_UNKNOWN",
    "FILTER_ARM",
    "FILTER_ARMTHUMB",
    "FILTER_DELTA",
    "FILTER_IA64",
    "FILTER_LZMA1",
    "FILTER_LZMA2",
    "FILTER_POWERPC",
    "FILTER_SPARC",
    "FILTER_X86",
    "MF_BT2",
    "MF_BT3",
    "MF_BT4",
    "MF_HC3",
    "MF_HC4",
    "MODE_FAST",
    "MODE_NORMAL",
    "PRESET_DEFAULT",
    "PRESET_EXTREME",
    "compress",
    "decompress",
    "is_check_supported",
)
