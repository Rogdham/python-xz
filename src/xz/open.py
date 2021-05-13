from io import TextIOWrapper

from xz.file import XZFile


class _XZFileText(TextIOWrapper):
    def __init__(self, filename, mode, encoding, errors, newline):
        self.xz_file = XZFile(filename, mode.replace("t", ""))
        super().__init__(self.xz_file, encoding, errors, newline)

    @property
    def stream_boundaries(self):
        return self.xz_file.stream_boundaries

    @property
    def block_boundaries(self):
        return self.xz_file.block_boundaries


def xz_open(filename, mode="rb", *, encoding=None, errors=None, newline=None):
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

        return _XZFileText(filename, mode, encoding, errors, newline)

    if encoding is not None:
        raise ValueError("Argument 'encoding' not supported in binary mode")
    if errors is not None:
        raise ValueError("Argument 'errors' not supported in binary mode")
    if newline is not None:
        raise ValueError("Argument 'newline' not supported in binary mode")

    return XZFile(filename, mode)
