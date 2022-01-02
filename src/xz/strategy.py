import time
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:  # pragma: no cover
    # avoid circular dependency
    from xz.block import XZBlock


class KeepBlockReadStrategy:
    def on_create(self, block: "XZBlock") -> None:
        pass  # do nothing

    def on_delete(self, block: "XZBlock") -> None:
        pass  # do nothing

    def on_read(self, block: "XZBlock") -> None:
        pass  # do nothing


class RollingBlockReadStrategy:
    def __init__(self, max_block_read_nb: int = 8) -> None:
        self.block_reads: Dict["XZBlock", float] = {}
        self.max_block_read_nb = max_block_read_nb

    def _freshly_used(self, block: "XZBlock") -> None:
        self.block_reads[block] = time.monotonic()

    def on_create(self, block: "XZBlock") -> None:
        self._freshly_used(block)
        if len(self.block_reads) > self.max_block_read_nb:
            to_clear = min(
                self.block_reads.items(),
                key=lambda item: item[1],
            )[0]
            to_clear.clear()  # will call on_delete

    def on_delete(self, block: "XZBlock") -> None:
        del self.block_reads[block]

    def on_read(self, block: "XZBlock") -> None:
        self._freshly_used(block)
