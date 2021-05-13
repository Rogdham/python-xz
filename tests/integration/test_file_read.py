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
                assert (  # pylint: disable=protected-access
                    block._length == metadata_block["length"]
                )
                pos += metadata_block["length"]
            stream_length = pos - stream_pos
            assert stream._length == stream_length  # pylint: disable=protected-access
        assert xz_file.stream_boundaries == stream_boundaries
        assert xz_file.block_boundaries == block_boundaries
        assert xz_file.read() == data_pattern
