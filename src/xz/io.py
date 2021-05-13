from io import SEEK_CUR, SEEK_END, SEEK_SET, IOBase

from xz.utils import FloorDict


class IOAbstract(IOBase):
    def __init__(self, length):
        super().__init__()
        self._pos = 0
        self._length = length

    def __repr__(self):
        return f"<{self.__class__.__name__} object at {hex(hash(self))}>"

    def seek(self, pos, whence=SEEK_SET):
        """Change stream position.

        Change the stream position to byte offset pos. Argument pos is
        interpreted relative to the position indicated by whence. Values
        for whence are ints:

        * 0 -- start of stream (the default); offset should be zero or positive
        * 1 -- current stream position; offset may be negative
        * 2 -- end of stream; offset should be negative

        Return an int indicating the new absolute position.
        """
        if whence == SEEK_SET:
            pass
        elif whence == SEEK_CUR:
            pos += self._pos
        elif whence == SEEK_END:
            pos += self._length
        else:
            raise ValueError("unsupported whence value")
        if 0 <= pos <= self._length:
            self._pos = pos
            return self._pos
        raise ValueError("invalid seek position")

    def tell(self):
        """Return an int indicating the current stream position."""
        return self._pos

    def readable(self):
        """Return a bool indicating whether object was opened for reading."""
        return True

    def seekable(self):
        """Return a bool indicating whether object supports random access."""
        return True

    def writable(self):
        """Return a bool indicating whether object was opened for writing."""
        return False

    def read(self, size=-1):
        """Read at most size bytes, returned as a bytes object.

        If the size argument is negative, read until EOF is reached.
        Return an empty bytes object at EOF.
        """
        if size < 0:
            size = self._length
        size = min(size, self._length - self._pos)
        parts = []
        while size:
            data = self._read(size)  # do not stop if data is empty
            parts.append(data)
            size -= len(data)
            self._pos += len(data)
        return b"".join(parts)

    def _read(self, size):  # pragma: no cover
        """Read and return up to size bytes, where size is an int.

        The size will not exceed the number of bytes between self._pos and
        self_length. This should prevent to deal with EOF.

        This function can return less bytes than size, in which case it will be
        called again. This includes being able to return an empty bytes object.
        """
        raise NotImplementedError  # must be overridden


class IOStatic(IOAbstract):
    def __init__(self, data):
        self.data = bytearray(data)
        super().__init__(len(self.data))

    def _read(self, size):
        return self.data[self._pos : self._pos + size]


class IOProxy(IOAbstract):
    def __init__(self, fileobj, start, end):
        super().__init__(end - start)
        self.fileobj = fileobj
        self.start = start

    def _read(self, size):
        self.fileobj.seek(self.start + self._pos, SEEK_SET)
        return self.fileobj.read(size)  # size already restricted by caller


class IOCombiner(IOAbstract):
    def __init__(self, *fileobjs):
        super().__init__(0)
        self._fileobjs = FloorDict()
        for fileobj in fileobjs:
            self._append(fileobj)

    def _read(self, size):
        start, fileobj = self._fileobjs[self._pos, True]
        fileobj.seek(self._pos - start, SEEK_SET)
        return fileobj.read(size)

    def _append(self, fileobj):
        if not isinstance(fileobj, IOAbstract):
            raise TypeError
        self._fileobjs[self._length] = fileobj  # override empty streams
        self._length += fileobj._length  # pylint: disable=protected-access
