from io import DEFAULT_BUFFER_SIZE, SEEK_SET
from lzma import FORMAT_XZ, LZMACompressor, LZMADecompressor, LZMAError

from xz.common import (
    XZError,
    create_xz_header,
    create_xz_index_footer,
    parse_xz_footer,
    parse_xz_index,
)
from xz.io import IOAbstract, IOCombiner, IOStatic


class BlockRead:
    read_size = DEFAULT_BUFFER_SIZE

    def __init__(self, fileobj, check, unpadded_size, uncompressed_size):
        self.length = uncompressed_size
        self.fileobj = IOCombiner(
            IOStatic(create_xz_header(check)),
            fileobj,
            IOStatic(
                create_xz_index_footer(check, [(unpadded_size, uncompressed_size)])
            ),
        )
        self.reset()

    def reset(self):
        self.fileobj.seek(0, SEEK_SET)
        self.pos = 0
        self.decompressor = LZMADecompressor(format=FORMAT_XZ)

    def decompress(self, pos, size):
        if pos < self.pos:
            self.reset()

        skip_before = pos - self.pos

        # pylint: disable=using-constant-test
        if self.decompressor.eof:
            raise XZError("block: decompressor eof")

        if self.decompressor.needs_input:
            data_input = self.fileobj.read(self.read_size)
            if not data_input:
                raise XZError("block: data eof")
        else:
            data_input = b""

        data_output = self.decompressor.decompress(data_input, skip_before + size)
        self.pos += len(data_output)

        if self.pos == self.length:
            # we reached the end of the block
            # according to the XZ specification, we must check the
            # remaining bytes of the block; this is mainly performed by the
            # decompressor itself when we consume it
            while not self.decompressor.eof:
                if self.decompress(self.pos, 1):
                    raise LZMAError("Corrupt input data")

        return data_output[skip_before:]


class BlockWrite:
    def __init__(self, fileobj, check, preset, filters):
        self.fileobj = fileobj
        self.check = check
        self.compressor = LZMACompressor(FORMAT_XZ, check, preset, filters)
        self.pos = 0
        if self.compressor.compress(b"") != create_xz_header(check):
            raise XZError("block: compressor header")

    def _write(self, data):
        if data:
            self.fileobj.seek(self.pos)
            self.fileobj.write(data)
            self.pos += len(data)

    def compress(self, data):
        self._write(self.compressor.compress(data))

    def finish(self):
        data = self.compressor.flush()

        # footer
        check, backward_size = parse_xz_footer(data[-12:])
        if check != self.check:
            raise XZError("block: compressor footer check")

        # index
        records = parse_xz_index(data[-12 - backward_size : -12])
        if len(records) != 1:
            raise XZError("block: compressor index records length")

        # remaining block data
        self._write(data[: -12 - backward_size])

        return records[0]  # (unpadded_size, uncompressed_size)


class XZBlock(IOAbstract):
    def __init__(
        self,
        fileobj,
        check,
        unpadded_size,
        uncompressed_size,
        preset=None,
        filters=None,
    ):
        super().__init__(uncompressed_size)
        self.fileobj = fileobj
        self.check = check
        self.preset = preset
        self.filters = filters
        self.unpadded_size = unpadded_size
        self.operation = None

    @property
    def uncompressed_size(self):
        return self._length

    def _read(self, size):
        # enforce read mode
        if not isinstance(self.operation, BlockRead):
            self._write_end()
            self.operation = BlockRead(
                self.fileobj,
                self.check,
                self.unpadded_size,
                self.uncompressed_size,
            )

        # read data
        try:
            return self.operation.decompress(self._pos, size)
        except LZMAError as ex:
            raise XZError(f"block: error while decompressing: {ex}") from ex

    def writable(self):
        return isinstance(self.operation, BlockWrite) or not self._length

    def _write(self, data):
        # enforce write mode
        if not isinstance(self.operation, BlockWrite):
            self.operation = BlockWrite(
                self.fileobj,
                self.check,
                self.preset,
                self.filters,
            )

        # write data
        self.operation.compress(data)
        return len(data)

    def _write_after(self):
        if isinstance(self.operation, BlockWrite):
            self.unpadded_size, uncompressed_size = self.operation.finish()
            if uncompressed_size != self.uncompressed_size:
                raise XZError("block: compressor uncompressed size")
            self.operation = None

    def _truncate(self, size):
        # thanks to the writable method, we are sure that length is zero
        # so we don't need to handle the case of truncating in middle of the block
        self.seek(size)
        self.write(b"")
