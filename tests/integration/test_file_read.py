from xz import XZFile


def test_read_all(integration_case, data_pattern):
    xz_path, metadata = integration_case
    with XZFile(xz_path) as xz_file:
        streams_items = list(
            xz_file._fileobjs.items()  # pylint: disable=protected-access
        )
        assert len(streams_items) == len(metadata["streams"])
        pos = 0
        stream_boundaries = []
        block_boundaries = []
        for stream_item, metadata_stream in zip(streams_items, metadata["streams"]):
            stream_boundaries.append(pos)
            stream_pos, stream = stream_item
            assert stream_pos == pos
            assert stream.check == metadata_stream["check"]
            block_items = list(
                stream._fileobjs.items()  # pylint: disable=protected-access
            )
            assert len(block_items) == len(metadata_stream["blocks"])
            for block_item, metadata_block in zip(
                block_items, metadata_stream["blocks"]
            ):
                block_boundaries.append(pos)
                block_pos, block = block_item
                assert block_pos == pos - stream_pos
                assert len(block) == metadata_block["length"]
                pos += metadata_block["length"]
            assert len(stream) == pos - stream_pos
        assert xz_file.stream_boundaries == stream_boundaries
        assert xz_file.block_boundaries == block_boundaries
        assert xz_file.read() == data_pattern


def test_read_reversed(integration_case, data_pattern):
    xz_path, _ = integration_case
    with XZFile(xz_path) as xz_file:
        # we are testing the worst possible case (lots of negative seeking)
        # limit the time to test by reading in chunks instead of 1 byte at a time
        read_size = 37
        for pos in reversed(range(0, len(data_pattern), read_size)):
            xz_file.seek(pos)
            assert xz_file.read(read_size) == data_pattern[pos : pos + read_size]
