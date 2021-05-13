from io import DEFAULT_BUFFER_SIZE, SEEK_SET
from lzma import FORMAT_XZ, LZMADecompressor, LZMAError

from xz.common import XZError, create_xz_header, create_xz_index_footer
from xz.io import IOAbstract, IOCombiner, IOStatic


class XZBlock(IOAbstract):
    compressed_read_size = DEFAULT_BUFFER_SIZE

    def __init__(self, fileobj, check, unpadded_size, uncompressed_size):
        super().__init__(uncompressed_size)
        self.compressed_fileobj = IOCombiner(
            IOStatic(create_xz_header(check)),
            fileobj,
            IOStatic(
                create_xz_index_footer(check, [(unpadded_size, uncompressed_size)])
            ),
        )
        self._decompressor_reset()

    def _decompressor_reset(self):
        self.compressed_fileobj.seek(0, SEEK_SET)
        self.decompressor = LZMADecompressor(format=FORMAT_XZ)

    def _decompressor_read(self, size):
        # pylint: disable=using-constant-test
        if self.decompressor.eof:
            raise XZError("block: decompressor eof")
        if self.decompressor.needs_input:
            data_input = self.compressed_fileobj.read(self.compressed_read_size)
            if not data_input:
                raise XZError("block: data eof")
        else:
            data_input = b""
        return self.decompressor.decompress(data_input, size)

    def seek(self, *args):
        old_pos = self._pos
        super().seek(*args)
        pos_diff = self._pos - old_pos
        if pos_diff < 0:
            self._decompressor_reset()
            old_pos = 0
            pos_diff = self._pos
        if pos_diff > 0:
            self._pos = old_pos
            self.read(pos_diff)

    def _read(self, size):
        try:
            data_output = self._decompressor_read(size)

            if self._pos + len(data_output) == self._length:
                # we reached the end of the block
                # according to the XZ specification, we must check the
                # remaining bytes of the block; this is mainly performed by the
                # decompressor itself when we consume it
                while not self.decompressor.eof:
                    if self._decompressor_read(1):
                        raise LZMAError("Corrupt input data")

            return data_output

        except LZMAError as ex:
            raise XZError(f"block: error while decompressing: {ex}") from ex
