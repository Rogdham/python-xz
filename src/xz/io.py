from io import (
    DEFAULT_BUFFER_SIZE,
    SEEK_CUR,
    SEEK_END,
    SEEK_SET,
    IOBase,
    UnsupportedOperation,
)
from typing import IO, Generic, Optional, TypeVar, Union, cast

from xz.utils import FloorDict

#
# Typing note
#
# The consensus seems to favour IO instead of IOBase for typing.
# However we cannot subclass IO[bytes] in IOAbstract as it conflicts with IOBase.
#
# As a result, some casting or unions between IOAbstract and IO[bytes] may be required internally.
#


class IOAbstract(IOBase):
    def __init__(self, length: int) -> None:
        super().__init__()
        self._pos = 0
        self._length = length
        self._modified = False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} object at {hex(hash(self))}>"

    def __len__(self) -> int:
        return self._length

    def _check_not_closed(self) -> None:
        # https://github.com/PyCQA/pylint/issues/3484
        # pylint: disable=using-constant-test
        if self.closed:
            raise ValueError("I/O operation on closed file")

    def fileno(self) -> int:
        try:
            return cast(IO[bytes], self.fileobj).fileno()  # type: ignore[attr-defined]
        except AttributeError:
            raise UnsupportedOperation("fileno")  # pylint: disable=raise-missing-from

    def seekable(self) -> bool:
        """Return a bool indicating whether object supports random access."""
        return True

    def readable(self) -> bool:
        """Return a bool indicating whether object was opened for reading."""
        return True

    def writable(self) -> bool:
        """Return a bool indicating whether object was opened for writing."""
        return True

    def seek(self, pos: int, whence: int = SEEK_SET) -> int:
        """Change stream position.

        Change the stream position to byte offset pos. Argument pos is
        interpreted relative to the position indicated by whence. Values
        for whence are ints:

        * 0 -- start of stream (the default); offset should be zero or positive
        * 1 -- current stream position; offset may be negative
        * 2 -- end of stream; offset should be negative

        Return an int indicating the new absolute position.
        """
        self._check_not_closed()
        if not self.seekable():  # just in case seekable is overridden
            raise UnsupportedOperation("seek")
        if whence == SEEK_SET:
            pass
        elif whence == SEEK_CUR:
            pos += self._pos
        elif whence == SEEK_END:
            pos += self._length
        else:
            raise ValueError("unsupported whence value")
        if pos >= 0:
            self._pos = pos
            return self._pos
        raise ValueError("invalid seek position")

    def tell(self) -> int:
        """Return an int indicating the current stream position."""
        self._check_not_closed()
        return self._pos

    def read(self, size: int = -1) -> bytes:
        """Read at most size bytes, returned as a bytes object.

        If the size argument is negative, read until EOF is reached.
        Return an empty bytes object at or after EOF.
        """
        self._check_not_closed()
        if not self.readable():
            raise UnsupportedOperation("read")
        if size < 0:
            size = self._length
        size = min(size, self._length - self._pos)
        parts = []
        while size > 0:
            data = self._read(size)  # do not stop if nothing was read
            parts.append(data)
            size -= len(data)
            self._pos += len(data)
        return b"".join(parts)

    def _write_start(self) -> None:
        if not self._modified:
            self._write_before()
            self._modified = True

    def _write_end(self) -> None:
        if self._modified:
            self._write_after()
            self._modified = False

    def write(self, data: bytes) -> int:
        """Write data, passed as a bytes object.

        Returns the number of bytes written, which is always the length
        of the input data in bytes.
        """
        self._check_not_closed()
        if not self.writable():
            raise UnsupportedOperation("write")
        written_bytes = len(data)
        padding_size = self._pos - self._length
        if padding_size < 0:
            raise ValueError("write is only supported from EOF")
        if padding_size > 0:
            null_bytes = memoryview(bytearray(DEFAULT_BUFFER_SIZE))
            self._pos = self._length
        data = memoryview(data)
        while padding_size or data:
            self._write_start()
            if padding_size > 0:
                # pad with null bytes, not counted in written_bytes
                padding = null_bytes[:padding_size]
                written_len = self._write(padding)  # do not stop if nothing was written
                padding_size -= written_len
            else:
                written_len = self._write(data)  # do not stop if nothing was written
                data = data[written_len:]
            self._pos += written_len
            self._length = max(self._length, self._pos)
        return written_bytes

    def truncate(self, size: Optional[int] = None) -> int:
        """Truncate file to size bytes.
        Size defaults to the current IO position as reported by tell().

        The current file position is unchanged.

        Return the new size.
        """
        self._check_not_closed()
        if not self.writable():
            raise UnsupportedOperation("truncate")
        if size is None:
            size = self._pos
        elif size < 0:
            raise ValueError("invalid truncate size")
        if size != self._length:
            self._write_start()
            pos = self._pos
            self._truncate(size)
            self._length = size
            self._pos = pos  # make sure position is unchanged
        return self._length

    def close(self) -> None:
        """Flush and close the stream.

        This method has no effect if it is already closed.
        """
        try:
            if not self.closed:
                self._write_end()
        finally:
            super().close()

    # the methods below are expected to be implemented by subclasses
    # pylint: disable=no-self-use

    def _read(self, size: int) -> bytes:  # pragma: no cover
        """Read and return up to size bytes, where size is an int.

        The size will not exceed the number of bytes between self._pos and
        self._length. This should prevent to deal with EOF.

        This method can return less bytes than size, in which case it will be
        called again. This includes being able to return an empty bytes object.
        """
        raise UnsupportedOperation("read")

    def _write_before(self) -> None:
        """This method is called before the first write operation."""

    def _write_after(self) -> None:
        """This method is called after the last write operation (usually on file close)."""

    def _write(self, data: bytes) -> int:  # pragma: no cover
        """Writes as many bytes from data as possible, and return the number
        of bytes written.

        data may be greater than the number of bytes between self._pos
        and self._length; self._length will be updated by caller afterwards.

        This method can return and int smaller than the length of data, in which
        case it will be called again. This includes being able to return 0.
        """
        raise UnsupportedOperation("write")

    def _truncate(self, size: int) -> None:  # pragma: no cover
        """Truncate the file to the given size.
        This resizing can extend or reduce the current file size.

        The current file position may be changed by this method,
        but is restored by caller.

        Returns None.
        """
        raise UnsupportedOperation("truncate")


class IOStatic(IOAbstract):
    def __init__(self, data: bytes) -> None:
        self.data = bytearray(data)
        super().__init__(len(self.data))

    def writable(self) -> bool:
        return False

    def _read(self, size: int) -> bytes:
        return self.data[self._pos : self._pos + size]


class IOProxy(IOAbstract):
    def __init__(
        self,
        fileobj: Union[IO[bytes], IOAbstract],  # see typing note on top of this file
        start: int,
        end: int,
    ) -> None:
        super().__init__(end - start)
        self.fileobj = fileobj
        self.start = start

    def _read(self, size: int) -> bytes:
        self.fileobj.seek(self.start + self._pos, SEEK_SET)
        return self.fileobj.read(size)  # size already restricted by caller

    def _write(self, data: bytes) -> int:
        self.fileobj.seek(self.start + self._pos, SEEK_SET)
        return self.fileobj.write(data)

    def _truncate(self, size: int) -> None:
        self.fileobj.truncate(self.start + size)


T = TypeVar("T", bound=IOAbstract)


class IOCombiner(IOAbstract, Generic[T]):
    def __init__(self, *fileobjs: T) -> None:
        super().__init__(0)
        self._fileobjs: FloorDict[T] = FloorDict()
        for fileobj in fileobjs:
            self._append(fileobj)

    def _get_fileobj(self) -> T:
        start, fileobj = self._fileobjs.get_with_index(self._pos)
        fileobj.seek(self._pos - start, SEEK_SET)
        return fileobj

    def _read(self, size: int) -> bytes:
        return self._get_fileobj().read(size)

    def _write_after(self) -> None:
        if self._fileobjs:
            last_fileobj = self._fileobjs.last_item
            if last_fileobj:
                last_fileobj._write_end()  # pylint: disable=protected-access
            else:
                del self._fileobjs[self._fileobjs.last_key]

    def _write(self, data: bytes) -> int:
        if self._fileobjs:
            fileobj: Optional[T] = self._get_fileobj()
        else:
            fileobj = None

        if fileobj is None or not fileobj.writable():
            self._change_fileobj()
            fileobj = self._get_fileobj()

        # newly created fileobj should be writable
        # otherwire this will raise UnsupportedOperation
        return fileobj.write(data)

    def _truncate(self, size: int) -> None:
        start, fileobj = self._fileobjs.get_with_index(size)
        if start != size:
            fileobj.truncate(size - start)
        for key in reversed(self._fileobjs):
            if key < size:
                break
            del self._fileobjs[key]

    def _append(self, fileobj: T) -> None:
        if not isinstance(fileobj, IOAbstract):
            raise TypeError
        self._fileobjs[self._length] = fileobj  # override empty streams
        self._length += len(fileobj)

    def _change_fileobj(self) -> None:
        """Create and append a new fileobj.

        If the last fileobj was empty, delete it.
        """
        # end write on last fileobj
        if self._fileobjs:
            last_fileobj = self._fileobjs.last_item
            if last_fileobj:
                if last_fileobj.writable():
                    last_fileobj._write_end()  # pylint: disable=protected-access
            else:
                del self._fileobjs[self._fileobjs.last_key]

        # create and append new fileobj
        self._append(self._create_fileobj())

    def _create_fileobj(self) -> T:  # pragma: no cover
        """
        Create a new fileobj to be concatenated.

        It must be writable.
        """
        raise NotImplementedError
