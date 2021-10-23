from functools import wraps
from io import TextIOWrapper

from xz.file import XZFile
from xz.utils import proxy_property


class _XZFileText(TextIOWrapper):
    def __init__(self, filename, mode, encoding, errors, newline, **kwargs):
        self.xz_file = XZFile(filename, mode.replace("t", ""), **kwargs)
        super().__init__(self.xz_file, encoding, errors, newline)

    check = proxy_property("check", "xz_file")
    preset = proxy_property("preset", "xz_file")
    filters = proxy_property("filters", "xz_file")
    stream_boundaries = proxy_property("stream_boundaries", "xz_file")
    block_boundaries = proxy_property("block_boundaries", "xz_file")

    @wraps(XZFile.change_stream)
    def change_stream(self):
        self.flush()
        self.xz_file.change_stream()

    @wraps(XZFile.change_block)
    def change_block(self):
        self.flush()
        self.xz_file.change_block()


def xz_open(filename, mode="rb", *, encoding=None, errors=None, newline=None, **kwargs):
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

        return _XZFileText(filename, mode, encoding, errors, newline, **kwargs)

    if encoding is not None:
        raise ValueError("Argument 'encoding' not supported in binary mode")
    if errors is not None:
        raise ValueError("Argument 'errors' not supported in binary mode")
    if newline is not None:
        raise ValueError("Argument 'newline' not supported in binary mode")

    return XZFile(filename, mode, **kwargs)
