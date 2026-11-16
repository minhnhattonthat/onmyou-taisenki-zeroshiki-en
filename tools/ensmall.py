"""English glyphs for the game's small 8x8 font (resource type 12, docs/re/font.md "Small font"), and their widths.

The small font holds one 8x8 4bpp tile per Shift-JIS code 0x8140..0x839F (code + 0x7EC0 = its index). It draws the
battle speaker name tag (0x08111B50, 5 OBJ tiles = 40 px) and a few fixed-cell labels. The build overwrites the
glyphs at enfont.CODES with the narrow art below; the tag plotter in tools/vwf.py (`tag`) advances by `width`.

    python -X utf8 tools/ensmall.py            # self-test
    python -X utf8 tools/ensmall.py --sheet    # print every glyph as nibble art

Art: rows top to bottom, '#' = body (colour F). Row 5 = baseline, row 6 = descender. The build adds the game's own
drop shadow (colour E, right, below and right-below of every body pixel). Advance = art width + 1 (the shadow).
"""
import sys

import enfont

SPACE_W = 3
TAG_PX = 56   # the battle name tag: OBJ 32x8 + 32x8 at tiles 0x3D3..0x3DA (vwf.tag_tiles), centred on x 40

ART = {
    "A": ".##. #..# #..# #### #..# #..#",
    "B": "###. #..# ###. #..# #..# ###.",
    "C": ".### #... #... #... #... .###",
    "D": "###. #..# #..# #..# #..# ###.",
    "E": "#### #... ###. #... #... ####",
    "F": "#### #... ###. #... #... #...",
    "G": ".### #... #.## #..# #..# .###",
    "H": "#..# #..# #### #..# #..# #..#",
    "I": "### .#. .#. .#. .#. ###",
    "J": "...# ...# ...# ...# #..# .##.",
    "K": "#..# #.#. ##.. #.#. #..# #..#",
    "L": "#... #... #... #... #... ####",
    "M": "#...# ##.## #.#.# #...# #...# #...#",
    "N": "#..# ##.# #.## #..# #..# #..#",
    "O": ".##. #..# #..# #..# #..# .##.",
    "P": "###. #..# #..# ###. #... #...",
    "Q": ".##. #..# #..# #..# #.#. .#.#",
    "R": "###. #..# #..# ###. #.#. #..#",
    "S": ".### #... .##. ...# ...# ###.",
    "T": "##### ..#.. ..#.. ..#.. ..#.. ..#..",
    "U": "#..# #..# #..# #..# #..# .##.",
    "V": "#...# #...# #...# .#.#. .#.#. ..#..",
    "W": "#...# #...# #.#.# #.#.# ##.## #...#",
    "X": "#..# #..# .##. .##. #..# #..#",
    "Y": "#...# .#.#. ..#.. ..#.. ..#.. ..#..",
    "Z": "#### ...# ..#. .#.. #... ####",
    "a": ".... .... .### #..# #..# .###",
    "b": "#... #... ###. #..# #..# ###.",
    "c": "... ... .## #.. #.. .##",
    "d": "...# ...# .### #..# #..# .###",
    "e": ".... .... .##. #### #... .###",
    "f": ".## #.. ### #.. #.. #..",
    "g": ".... .... .### #..# .### ...# ###.",
    "h": "#... #... ###. #..# #..# #..#",
    "i": "# . # # # #",
    "j": ".# .. .# .# .# .# #.",
    "k": "#... #... #..# ###. #.#. #..#",
    "l": "# # # # # #",
    "m": "..... ..... ####. #.#.# #.#.# #.#.#",
    "n": ".... .... ###. #..# #..# #..#",
    "o": ".... .... .##. #..# #..# .##.",
    "p": ".... .... ###. #..# #..# ###. #...",
    "q": ".... .... .### #..# #..# .### ...#",
    "r": "... ... #.# ##. #.. #..",
    "s": ".... .... .### ##.. ..## ###.",
    "t": ".#. .#. ### .#. .#. ..#",
    "u": ".... .... #..# #..# #..# .###",
    "v": ".... .... #..# #..# .##. .##.",
    "w": "..... ..... #...# #.#.# #.#.# .#.#.",
    "x": ".... .... #..# .##. .##. #..#",
    "y": ".... .... #..# #..# .### ...# .##.",
    "z": ".... .... #### ..#. .#.. ####",
    "0": ".##. #..# #.## ##.# #..# .##.",
    "1": ".#. ##. .#. .#. .#. ###",
    "2": ".##. #..# ..#. .#.. #... ####",
    "3": "###. ...# .##. ...# ...# ###.",
    "4": "#..# #..# #### ...# ...# ...#",
    "5": "#### #... ###. ...# ...# ###.",
    "6": ".##. #... ###. #..# #..# .##.",
    "7": "#### ...# ..#. .#.. .#.. .#..",
    "8": ".##. #..# .##. #..# #..# .##.",
    "9": ".##. #..# #..# .### ...# .##.",
    "!": "# # # # . #",
    "?": "###. ...# .##. .#.. .... .#..",
    ".": ". . . . . #",
    ",": ".. .. .. .. .. .# #.",
    "'": "# # . . . .",
    "‘": "# # . . . .",
    '"': "#.# #.# ... ... ... ...",
    "“": "#.# #.# ... ... ... ...",
    "-": "... ... ### ... ... ...",
    "—": "..... ..... ##### ..... ..... .....",
    "…": "..... ..... ..... ..... ..... #.#.#",
    ":": ". # . . # .",
    ";": ".. .# .. .. .# #.",
    "(": ".# #. #. #. #. .#",
    ")": "#. .# .# .# .# #.",
    "[": "## #. #. #. #. ##",
    "]": "## .# .# .# .# ##",
    "/": "..# ..# .#. .#. #.. #..",
    "&": ".#.. #.#. .#.. #.## #.#. .#.#",
    "+": "... .#. ### .#. ... ...",
    "=": "... ### ... ### ... ...",
    "*": "... #.# .#. #.# ... ...",
    "<": "... ..# .#. #.. .#. ..#",
    ">": "... #.. .#. ..# .#. #..",
    "_": ".... .... .... .... .... ####",
    "~": ".... .#.# #.#. .... .... ....",
    "%": "#..# ...# ..#. .#.. #... #..#",
    "$": ".### #.#. .##. ..## #.#. ###.",
    "#": ".#.#. ##### .#.#. ##### .#.#. .....",
    "@": ".###. #...# #.### #.#.# #.##. .###.",
    "♪": "..## ..#. ..#. .##. ###. .#..",
    "\t": ".......",  # wide blank (enfont "\t")
}


def rows(ch):
    return ART[ch].split()


def width(ch):
    """Advance in pixels."""
    if ch == " ":
        return SPACE_W
    return len(rows(ch)[0]) + 1


def text_width(s):
    return sum(width(c) for c in s)


def glyph(ch):
    """32 bytes: one 8x8 4bpp tile, body F, drop shadow E."""
    px = [[0] * 8 for _ in range(8)]
    for y, r in enumerate(rows(ch)):
        for x, c in enumerate(r):
            if c == "#":
                px[y][x] = 0xF
    for y in range(8):
        for x in range(8):
            if px[y][x] == 0 and any(px[yy][xx] == 0xF for yy, xx in ((y - 1, x), (y, x - 1), (y - 1, x - 1))
                                     if yy >= 0 and xx >= 0):
                px[y][x] = 0xE
    out = bytearray(32)
    for y in range(8):
        for x in range(0, 8, 2):
            out[y * 4 + x // 2] = px[y][x] | px[y][x + 1] << 4
    return bytes(out)


def widths(ncodes):
    """One byte per code 0x8140..: small-font advance for English codes, 8 (the game's cell) elsewhere."""
    t = bytearray([8]) * ncodes
    for ch, code in enfont.CODES.items():
        t[code - 0x8140] = width(ch)
    t[enfont.NEWLINE - 0x8140] = 0
    return bytes(t)


def selftest():
    for ch in enfont.CODES:
        if ch == " ":
            continue
        assert ch in ART, "no small art for %r" % ch
        rs = rows(ch)
        assert len(rs) <= 7, ch
        assert len(set(map(len, rs))) == 1, "ragged rows in %r" % ch
        assert len(rs[0]) <= 7, ch
    assert text_width("Kogenta") <= TAG_PX


if __name__ == "__main__":
    selftest()
    if "--sheet" in sys.argv:
        for ch in ART:
            print(ch, width(ch))
            g = glyph(ch)
            for y in range(8):
                print("  " + "".join(".123456789ABCDEF"[(g[y * 4 + x // 2] >> (4 * (x & 1))) & 15] for x in range(8)))
    print("ok: %d small glyphs, Kogenta %d px" % (len(ART), text_width("Kogenta")))
