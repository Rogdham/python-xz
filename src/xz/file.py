from io import SEEK_CUR, SEEK_END
import os

from xz.common import XZError
from xz.io import IOCombiner
from xz.stream import XZStream


class XZFile(IOCombiner):
    """A file object providing transparent XZ (de)compression.

    An XZFile can act as a wrapper for an existing file object, or
    refer directly to a named file on disk.

    Note that XZFile provides a *binary* file interface - data read
    is returned as bytes, and data to be written must be given as bytes.
    Use xz.open if you want a *text* file interface.
    """

    def __init__(self, filename=None, mode="r"):
        """Open an XZ file in binary mode.

        filename can be either an actual file name (given as a str,
        bytes, or PathLike object), in which case the named file is
        opened, or it can be an existing file object to read from or
        write to.

        mode can be "r" for reading (default).
        It is equivalent to "rb".
        """

        self.close_fileobj = False
        self.mode = mode
        if self.mode.endswith("b"):
            self.mode = self.mode[:-1]

        super().__init__()

        if isinstance(filename, (str, bytes, os.PathLike)):
            # pylint: disable=consider-using-with
            self.fileobj = open(filename, self.mode + "b")
            self.close_fileobj = True
        elif hasattr(filename, "read"):
            self.fileobj = filename
        else:
            raise TypeError("filename must be a str, bytes, file or PathLike object")

        # we only support read for now
        if self.mode in ("r", "rb"):
            self._init_parse()
        else:
            raise ValueError(f"invalid mode: {mode}")

    def close(self):
        try:
            super().close()
        finally:
            if self.close_fileobj:
                self.fileobj.close()

    @property
    def stream_boundaries(self):
        return list(self._fileobjs)

    @property
    def block_boundaries(self):
        return [
            stream_pos + block_boundary
            for stream_pos, stream in self._fileobjs.items()
            for block_boundary in stream.block_boundaries
        ]

    def _init_parse(self):
        self.fileobj.seek(0, SEEK_END)

        streams = []

        while self.fileobj.tell():
            if self.fileobj.tell() % 4:
                raise XZError("file: invalid size")
            self.fileobj.seek(-4, SEEK_CUR)
            if any(self.fileobj.read(4)):
                streams.append(XZStream.parse(self.fileobj))
            else:
                self.fileobj.seek(-4, SEEK_CUR)  # stream padding

        if not streams:
            raise XZError("file: no streams")

        while streams:
            self._append(streams.pop())
