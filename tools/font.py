"""The 16x16 dialogue/menu font (docs/re/font.md): glyph lookup, decode, encode.

    python -X utf8 tools/font.py show ROM CODE..     # print glyphs as nibble art (CODE = Shift-JIS hex, e.g. 82A0)

Glyph = 128 bytes, 2x2 GBA 4bpp tiles in the order TL, TR, BL, BR.
"""
import struct
import sys

INDEX = 0x3E17CA          # header 0d00 4017 1000 1000, then int16 slot[code - 0x8140]
ENTRIES = 0x3E8C68        # 12-byte entries; ((e[8] & 0xFFF) << 16) + e[10] = offset into glyph data
FILETAB = 0x4028EC        # file table; entry 13's data pointer at +0x68
NCODES = 0x1740


def glyph_data_base(rom):
    return struct.unpack_from("<I", rom, FILETAB + 0x68)[0] & 0x01FFFFFF


def glyph_offset(rom, code):
    """ROM offset of the glyph for Shift-JIS code (big-endian value, e.g. 0x82A0), or None."""
    i = code - 0x8140
    if not 0 <= i < NCODES:
        return None
    slot = struct.unpack_from("<h", rom, INDEX + 8 + 2 * i)[0]
    if slot < 0:
        return None
    e = ENTRIES + slot * 2
    h8, h10 = struct.unpack_from("<HH", rom, e + 8)
    return glyph_data_base(rom) + ((h8 & 0xFFF) << 16) + h10


def decode(data):
    """128 bytes -> 16 rows of 16 nibbles."""
    px = [[0] * 16 for _ in range(16)]
    for t in range(4):
        tx, ty = (t & 1) * 8, (t >> 1) * 8
        for y in range(8):
            for x in range(8):
                b = data[t * 32 + y * 4 + x // 2]
                px[ty + y][tx + x] = (b >> 4) if x & 1 else (b & 15)
    return px


def encode(px):
    out = bytearray(128)
    for t in range(4):
        tx, ty = (t & 1) * 8, (t >> 1) * 8
        for y in range(8):
            for x in range(0, 8, 2):
                out[t * 32 + y * 4 + x // 2] = (px[ty + y][tx + x] & 15) | (px[ty + y][tx + x + 1] & 15) << 4
    return bytes(out)


def main():
    if len(sys.argv) < 4 or sys.argv[1] != "show":
        print(__doc__)
        return 1
    rom = open(sys.argv[2], "rb").read()
    for c in sys.argv[3:]:
        code = int(c, 16)
        off = glyph_offset(rom, code)
        print("%04X %s at %s" % (code, bytes([code >> 8, code & 255]).decode("cp932", "replace"),
                                 "%06X" % off if off is not None else "none"))
        if off is not None:
            for row in decode(rom[off:off + 128]):
                print("  " + "".join(".123456789ABCDEF"[v] for v in row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
