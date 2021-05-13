from binascii import crc32 as crc32int
from struct import pack, unpack

HEADER_MAGIC = b"\xfd7zXZ\x00"
FOOTER_MAGIC = b"YZ"


class XZError(Exception):
    pass


def encode_mbi(value):
    data = bytearray()
    while value >= 0x80:
        data.append((value | 0x80) & 0xFF)
        value >>= 7
    data.append(value)
    return data


def decode_mbi(data):
    value = 0
    for size, byte in enumerate(data):
        value |= (byte & 0x7F) << (size * 7)
        if not byte & 0x80:
            return (size + 1, value)
    raise XZError("invalid mbi")


def crc32(data):
    return pack("<I", crc32int(data))


def round_up(value):
    remainder = value % 4
    if remainder:
        return value - remainder + 4
    return value


def pad(value):
    return b"\x00" * (round_up(value) - value)


def create_xz_header(check):
    if not 0 <= check <= 0xF:
        raise XZError("header check")
    # stream header
    flags = pack("<BB", 0, check)
    return HEADER_MAGIC + flags + crc32(flags)


def create_xz_index_footer(check, records):
    if not 0 <= check <= 0xF:
        raise XZError("footer check")
    # index
    index = b"\x00"
    index += encode_mbi(len(records))
    for unpadded_size, uncompressed_size in records:
        index += encode_mbi(unpadded_size)
        index += encode_mbi(uncompressed_size)
    index += pad(len(index))
    index += crc32(index)
    # stream footer
    footer = pack("<IBB", (len(index) // 4) - 1, 0, check)
    footer = crc32(footer) + footer + FOOTER_MAGIC
    return index + footer


def parse_xz_header(header):
    if len(header) != 12:
        raise XZError("header length")
    if header[:6] != HEADER_MAGIC:
        raise XZError("header magic")
    if crc32(header[6:8]) != header[8:12]:
        raise XZError("header crc32")
    flag_first_byte, check = unpack("<BB", header[6:8])
    if flag_first_byte or not 0 <= check <= 0xF:
        raise XZError("header flags")
    return check


def parse_xz_index(index):
    if len(index) < 8 or len(index) % 4:
        raise XZError("index length")
    index = memoryview(index)
    if index[0]:
        raise XZError("index indicator")
    if crc32(index[:-4]) != index[-4:]:
        raise XZError("index crc32")
    size, nb_records = decode_mbi(index[1:])
    index = index[1 + size : -4]
    # records
    records = []
    for _ in range(nb_records):
        if not index:
            raise XZError("index size")
        size, unpadded_size = decode_mbi(index)
        if not unpadded_size:
            raise XZError("index record unpadded size")
        index = index[size:]
        if not index:
            raise XZError("index size")
        size, uncompressed_size = decode_mbi(index)
        if not uncompressed_size:
            raise XZError("index record uncompressed size")
        index = index[size:]
        records.append((unpadded_size, uncompressed_size))
    # index padding
    if any(index):
        raise XZError("index padding")
    return records


def parse_xz_footer(footer):
    if len(footer) != 12:
        raise XZError("footer length")
    if footer[10:12] != FOOTER_MAGIC:
        raise XZError("footer magic")
    if crc32(footer[4:10]) != footer[:4]:
        raise XZError("footer crc32")
    backward_size, flag_first_byte, check = unpack("<IBB", footer[4:10])
    backward_size = (backward_size + 1) * 4
    if flag_first_byte or not 0 <= check <= 0xF:
        raise XZError("footer flags")
    return (check, backward_size)
