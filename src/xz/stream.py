from io import SEEK_CUR
from typing import IO, List

from xz.block import XZBlock
from xz.common import (
    XZError,
    create_xz_header,
    create_xz_index_footer,
    parse_xz_footer,
    parse_xz_header,
    parse_xz_index,
    round_up,
)
from xz.io import IOCombiner, IOProxy
from xz.typing import _LZMAFiltersType, _LZMAPresetType


class XZStream(IOCombiner[XZBlock]):
    def __init__(
        self,
        fileobj: IOProxy,
        check: int,
        preset: _LZMAPresetType = None,
        filters: _LZMAFiltersType = None,
    ) -> None:
        super().__init__()
        self.fileobj = fileobj
        self._check = check
        self.preset = preset
        self.filters = filters

    @property
    def check(self) -> int:
        return self._check

    @property
    def block_boundaries(self) -> List[int]:
        return list(self._fileobjs)

    @property
    def _fileobj_blocks_end_pos(self) -> int:
        return 12 + sum(
            round_up(block.unpadded_size) for block in self._fileobjs.values()
        )

    @classmethod
    def parse(cls, fileobj: IO[bytes]) -> "XZStream":
        """Parse one XZ stream from a fileobj.

        fileobj position should be right at the end of the stream when calling
        and will be moved right at the start of the stream
        """
        # footer
        footer_end_pos = fileobj.seek(-12, SEEK_CUR) + 12
        footer = fileobj.read(12)
        check, backward_size = parse_xz_footer(footer)

        # index
        block_start = fileobj.seek(-12 - backward_size, SEEK_CUR)
        index = fileobj.read(backward_size)
        records = parse_xz_index(index)
        blocks_len = sum(round_up(unpadded_size) for unpadded_size, _ in records)
        block_start -= blocks_len
        blocks = []
        for unpadded_size, uncompressed_size in records:
            block_end = block_start + round_up(unpadded_size)
            blocks.append(
                XZBlock(
                    IOProxy(fileobj, block_start, block_end),
                    check,
                    unpadded_size,
                    uncompressed_size,
                )
            )
            block_start = block_end

        # header
        fileobj.seek(-12 - blocks_len - backward_size, SEEK_CUR)
        header = fileobj.read(12)
        header_check = parse_xz_header(header)
        if header_check != check:
            raise XZError("stream: inconsistent check value")

        header_start_pos = fileobj.seek(-12, SEEK_CUR)

        stream_fileobj = IOProxy(fileobj, header_start_pos, footer_end_pos)
        stream = cls(stream_fileobj, check)
        for block in blocks:
            stream._append(block)
        return stream

    def _create_fileobj(self) -> XZBlock:
        self.fileobj.truncate(self._fileobj_blocks_end_pos)
        return XZBlock(
            IOProxy(
                self.fileobj,
                self._fileobj_blocks_end_pos,
                self._fileobj_blocks_end_pos,
            ),
            self.check,
            0,
            0,
            self.preset,
            self.filters,
        )

    def _write_before(self) -> None:
        if not self:
            self.fileobj.seek(0)
            self.fileobj.truncate()
            self.fileobj.write(create_xz_header(self.check))

    def _write_after(self) -> None:
        super()._write_after()
        self.fileobj.seek(self._fileobj_blocks_end_pos)
        self.fileobj.truncate()
        self.fileobj.write(
            create_xz_index_footer(
                self.check,
                [
                    (block.unpadded_size, block.uncompressed_size)
                    for block in self._fileobjs.values()
                ],
            )
        )

    def change_block(self) -> None:
        """
        End the current block, and create a new one.

        If the current block is empty, replace it instead."""
        if self._fileobjs:
            self._change_fileobj()
