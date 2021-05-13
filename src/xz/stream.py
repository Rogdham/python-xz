from io import SEEK_CUR

from xz.block import XZBlock
from xz.common import (
    XZError,
    parse_xz_footer,
    parse_xz_header,
    parse_xz_index,
    round_up,
)
from xz.io import IOCombiner, IOProxy


class XZStream(IOCombiner):
    def __init__(self, check):
        super().__init__()
        self.check = check

    @property
    def block_boundaries(self):
        return list(self._fileobjs)

    @classmethod
    def parse(cls, fileobj):
        """Parse one XZ stream from a fileobj.

        fileobj position should be right at the end of the stream when calling
        and will be moved right at the start of the stream
        """
        # footer
        fileobj.seek(-12, SEEK_CUR)
        footer = fileobj.read(12)
        check, backward_size = parse_xz_footer(footer)
        stream = cls(check)

        # index
        block_start = fileobj.seek(-12 - backward_size, SEEK_CUR)
        index = fileobj.read(backward_size)
        records = parse_xz_index(index)
        blocks_len = sum(round_up(unpadded_size) for unpadded_size, _ in records)
        block_start -= blocks_len
        for unpadded_size, uncompressed_size in records:
            block_end = block_start + round_up(unpadded_size)
            stream._append(
                XZBlock(
                    IOProxy(fileobj, block_start, block_end),
                    stream.check,
                    unpadded_size,
                    uncompressed_size,
                )
            )
            block_start = block_end

        # header
        fileobj.seek(-12 - blocks_len - backward_size, SEEK_CUR)
        header = fileobj.read(12)
        header_check = parse_xz_header(header)
        if header_check != stream.check:
            raise XZError("stream: inconsistent check value")

        fileobj.seek(-12, SEEK_CUR)
        return stream
