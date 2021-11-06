from io import SEEK_CUR, SEEK_END
import os
from typing import IO, List, Optional
import warnings

from xz.common import DEFAULT_CHECK, XZError
from xz.io import IOCombiner, IOProxy
from xz.stream import XZStream
from xz.typing import _LZMAFilenameType, _LZMAFiltersType, _LZMAPresetType
from xz.utils import parse_mode, proxy_property


class XZFile(IOCombiner[XZStream]):
    """A file object providing transparent XZ (de)compression.

    An XZFile can act as a wrapper for an existing file object, or
    refer directly to a named file on disk.

    Note that XZFile provides a *binary* file interface - data read
    is returned as bytes, and data to be written must be given as bytes.
    Use xz.open if you want a *text* file interface.
    """

    def __init__(
        self,
        filename: _LZMAFilenameType,
        mode: str = "r",
        *,
        check: int = -1,
        preset: _LZMAPresetType = None,
        filters: _LZMAFiltersType = None
    ) -> None:
        """Open an XZ file in binary mode.

        The filename argument can be either an actual file name
        (given as a str, bytes, or PathLike object),
        in which case the named file is opened,
        or it can be an existing file object to read from or write to.

        The mode argument can be one of the following:
         - "r" for reading (default)
         - "w" for writing, truncating the file
         - "r+" for reading and writing
         - "w+" for reading and writing, truncating the file
         - "x" and "x+" are like "w" and "w+", except that an
           FileExistsError is raised if the file already exists

        The following arguments are used during writing:
         - check: when creating a new stream
         - preset: when creating a new block
         - filters: when creating a new block

        For more information about the check/preset/filters arguments,
        refer to the documentation of the lzma module.
        """
        self._close_fileobj = False
        self._close_check_empty = False

        super().__init__()

        self.mode, self._readable, self._writable = parse_mode(mode)

        # get fileobj
        if isinstance(filename, (str, bytes, os.PathLike)):
            # pylint: disable=consider-using-with, unspecified-encoding
            self.fileobj: IO[bytes] = open(filename, self.mode + "b")
            self._close_fileobj = True
        elif hasattr(filename, "read"):  # weak check but better than nothing
            self.fileobj = filename
        else:
            raise TypeError("filename must be a str, bytes, file or PathLike object")

        # check fileobj
        if not self.fileobj.seekable():
            raise ValueError("filename is not seekable")
        if self._readable and not self.fileobj.readable():
            raise ValueError("filename is not readable")
        if self._writable and not self.fileobj.writable():
            raise ValueError("filename is not writable")

        # init
        if self.mode[0] in "wx":
            self.fileobj.truncate(0)
        if self._readable:
            self._init_parse()
        if self.mode[0] == "r" and not self._fileobjs:
            raise XZError("file: no streams")

        self.check = check if check != -1 else DEFAULT_CHECK
        self.preset = preset
        self.filters = filters

        self._close_check_empty = self.mode[0] != "r"

    @property
    def _last_stream(self) -> Optional[XZStream]:
        try:
            return self._fileobjs.last_item
        except KeyError:
            return None

    preset: _LZMAPresetType = proxy_property("preset", "_last_stream")
    filters: _LZMAFiltersType = proxy_property("filters", "_last_stream")

    def readable(self) -> bool:
        return self._readable

    def writable(self) -> bool:
        return self._writable

    def close(self) -> None:
        try:
            super().close()
            if self._close_check_empty and not self:
                warnings.warn(
                    "Empty XZFile: nothing was written, "
                    "so output is empty (and not a valid xz file).",
                    RuntimeWarning,
                )
        finally:
            if self._close_fileobj:
                self.fileobj.close()  # self.fileobj exists at this point

    @property
    def stream_boundaries(self) -> List[int]:
        return list(self._fileobjs)

    @property
    def block_boundaries(self) -> List[int]:
        return [
            stream_pos + block_boundary
            for stream_pos, stream in self._fileobjs.items()
            for block_boundary in stream.block_boundaries
        ]

    def _init_parse(self) -> None:
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

        while streams:
            self._append(streams.pop())

    def _create_fileobj(self) -> XZStream:
        stream_pos = sum(len(stream.fileobj) for stream in self._fileobjs.values())
        return XZStream(
            IOProxy(
                self.fileobj,
                stream_pos,
                stream_pos,
            ),
            self.check,
            self.preset,
            self.filters,
        )

    def change_stream(self) -> None:
        """
        Create a new stream.

        If the current stream is empty, replace it instead."""
        if self._fileobjs:
            self._change_fileobj()

    def change_block(self) -> None:
        """
        Create a new block.

        If the current block is empty, replace it instead."""
        last_stream = self._last_stream
        if last_stream:
            last_stream.change_block()
