"""English font for the VWF (docs/re/font.md "English"): glyph art, widths, and the `en` encoder.

English is stored as Shift-JIS fullwidth codes (Ａ = 0x8260 ...), so the script parser and every string table work
unchanged; the build overwrites those codes' glyphs in the game's 16x16 font with the narrow glyphs below and writes
a width table that tools/vwf.py's renderer uses as the advance.

    python -X utf8 tools/enfont.py           # self-test + print the glyph sheet as text

Art: '#' = body pixel (colour F), drawn 1 px from the cell's left edge; the build adds a 1 px outline (colour E)
around it like the game's own glyphs. Row 0 = cap top (cell row 3), row 8 = baseline (cell row 11), rows 9-10 =
descenders. Advance = art width + SPACING.
"""
import sys

SPACING = 1        # px from one glyph's last body column to the next glyph's first (the shared outline column)
TOP = 3            # cell row of art row 0
SPACE_W = 4        # advance of ' ' (0x8140 has no glyph: the renderer skips it)
NEWLINE = 0x81AD   # no glyph; the VWF renderer starts a new line on it (string tables have no newline code)

# ASCII -> Shift-JIS code. Fullwidth forms where cp932 has them in JIS level 1; " and ' use the curly quotes.
CODES = {" ": 0x8140, "!": 0x8149, '"': 0x8168, "#": 0x8194, "$": 0x8190, "%": 0x8193, "&": 0x8195, "'": 0x8166,
         "(": 0x8169, ")": 0x816A, "*": 0x8196, "+": 0x817B, ",": 0x8143, "-": 0x817C, ".": 0x8144, "/": 0x815E,
         ":": 0x8146, ";": 0x8147, "<": 0x8183, "=": 0x8181, ">": 0x8184, "?": 0x8148, "@": 0x8197, "[": 0x816D,
         "]": 0x816E, "_": 0x8151, "~": 0x8160, "…": 0x8163, "—": 0x815C, "♪": 0x81F4, "*": 0x8196,
         "“": 0x8167, "‘": 0x8165}
CODES.update({chr(0x30 + i): 0x824F + i for i in range(10)})
CODES.update({chr(0x41 + i): 0x8260 + i for i in range(26)})
CODES.update({chr(0x61 + i): 0x8281 + i for i in range(26)})

ART = {
    "A": ".##. #..# #..# #..# #### #..# #..# #..# #..#",
    "B": "###. #..# #..# #..# ###. #..# #..# #..# ###.",
    "C": ".### #... #... #... #... #... #... #... .###",
    "D": "###. #..# #..# #..# #..# #..# #..# #..# ###.",
    "E": "#### #... #... #... ###. #... #... #... ####",
    "F": "#### #... #... #... ###. #... #... #... #...",
    "G": ".### #... #... #... #.## #..# #..# #..# .###",
    "H": "#..# #..# #..# #..# #### #..# #..# #..# #..#",
    "I": "### .#. .#. .#. .#. .#. .#. .#. ###",
    "J": "..# ..# ..# ..# ..# ..# ..# ..# ##.",
    "K": "#..# #..# #.#. ##.. #... ##.. #.#. #..# #..#",
    "L": "#... #... #... #... #... #... #... #... ####",
    "M": "#...# ##.## #.#.# #.#.# #...# #...# #...# #...# #...#",
    "N": "#..# ##.# ##.# #.## #.## #..# #..# #..# #..#",
    "O": ".##. #..# #..# #..# #..# #..# #..# #..# .##.",
    "P": "###. #..# #..# #..# ###. #... #... #... #...",
    "Q": ".##. #..# #..# #..# #..# #..# #.## #..# .##. ...#",
    "R": "###. #..# #..# #..# ###. #.#. #..# #..# #..#",
    "S": ".### #... #... #... .##. ...# ...# ...# ###.",
    "T": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
    "U": "#..# #..# #..# #..# #..# #..# #..# #..# .##.",
    "V": "#...# #...# #...# #...# .#.#. .#.#. .#.#. ..#.. ..#..",
    "W": "#...# #...# #...# #...# #.#.# #.#.# #.#.# ##.## #...#",
    "X": "#...# #...# .#.#. .#.#. ..#.. .#.#. .#.#. #...# #...#",
    "Y": "#...# #...# .#.#. .#.#. ..#.. ..#.. ..#.. ..#.. ..#..",
    "Z": "#### ...# ...# ..#. .#.. #... #... #... ####",
    "a": ". . . .##. ...# .### #..# #..# .###",
    "b": "#... #... #... ###. #..# #..# #..# #..# ###.",
    "c": ". . . .### #... #... #... #... .###",
    "d": "...# ...# ...# .### #..# #..# #..# #..# .###",
    "e": ". . . .##. #..# #### #... #... .###",
    "f": "..## .#.. .#.. ###. .#.. .#.. .#.. .#.. .#..",
    "g": ". . . .### #..# #..# #..# .### ...# ...# ###.",
    "h": "#... #... #... ###. #..# #..# #..# #..# #..#",
    "i": "# . . # # # # # #",
    "j": ".# .. .. .# .# .# .# .# .# .# #.",
    "k": "#... #... #... #..# #.#. ##.. #.#. #..# #..#",
    "l": "#. #. #. #. #. #. #. #. .#",
    "m": ". . . ####. #.#.# #.#.# #.#.# #.#.# #.#.#",
    "n": ". . . ###. #..# #..# #..# #..# #..#",
    "o": ". . . .##. #..# #..# #..# #..# .##.",
    "p": ". . . ###. #..# #..# #..# #..# ###. #... #...",
    "q": ". . . .### #..# #..# #..# #..# .### ...# ...#",
    "r": ". . . #.## ##.. #... #... #... #...",
    "s": ". . . .### #... .##. ...# ...# ###.",
    "t": ".#.. .#.. .#.. ###. .#.. .#.. .#.. .#.. ..##",
    "u": ". . . #..# #..# #..# #..# #..# .###",
    "v": ". . . #...# #...# .#.#. .#.#. ..#..",
    "w": ". . . #...# #...# #.#.# #.#.# .#.#.",
    "x": ". . . #...# .#.#. ..#.. .#.#. #...#",
    "y": ". . . #..# #..# #..# #..# .### ...# ...# ###.",
    "z": ". . . #### ...# ..#. .#.. #... ####",
    "0": ".##. #..# #..# #.## ##.# #..# #..# #..# .##.",
    "1": ".#. ##. .#. .#. .#. .#. .#. .#. ###",
    "2": ".##. #..# ...# ...# ..#. .#.. #... #... ####",
    "3": "###. ...# ...# ...# .##. ...# ...# ...# ###.",
    "4": "..#. .##. #.#. #.#. #.#. #### ..#. ..#. ..#.",
    "5": "#### #... #... ###. ...# ...# ...# ...# ###.",
    "6": ".##. #... #... ###. #..# #..# #..# #..# .##.",
    "7": "#### ...# ...# ..#. ..#. .#.. .#.. .#.. .#..",
    "8": ".##. #..# #..# #..# .##. #..# #..# #..# .##.",
    "9": ".##. #..# #..# #..# .### ...# ...# ...# .##.",
    "!": "# # # # # # . # #",
    "?": ".##. #..# ...# ..#. .#.. .#.. .... .#.. .#..",
    ".": ". . . . . . . # #",
    ",": ". . . . . . . .# .# #.",
    ":": ". . . # # . . # #",
    ";": ". . . .# .# .. .. .# .# #.",
    "'": "# # #.",
    '"': "#.# #.# #.#",
    "‘": ".# #. ##",
    "“": ".#.# #.#. ##.##",
    "-": ". . . . ### . . . .",
    "—": ". . . . ###### . . . .",
    "~": ". . . .#.# #.#. . . . .",
    "(": "..# .#. #.. #.. #.. #.. #.. .#. ..#",
    ")": "#.. .#. ..# ..# ..# ..# ..# .#. #..",
    "[": "## #. #. #. #. #. #. #. ##",
    "]": "## .# .# .# .# .# .# .# ##",
    "/": "...# ...# ..#. ..#. .#.. .#.. #... #... #...",
    "+": ". . . .#. .#. ### .#. .#. .",
    "=": ". . . . #### . #### . .",
    "<": ". . ...# ..#. .#.. #... .#.. ..#. ...#",
    ">": ". . #... .#.. ..#. ...# ..#. .#.. #...",
    "*": ". .#. ### .#. #.# . . . .",
    "&": ".#.. #.#. #.#. .#.. .#.# #.#. #..# #..# .##.#",
    "%": "##..# ##..# ...#. ..#.. ..#.. .#... #..## #..## .....",
    "#": ". .#.#. ##### .#.#. .#.#. ##### .#.#. . .",
    "$": "..#.. .#### #.#.. #.#.. .###. ..#.# ..#.# ####. ..#..",
    "@": ".###. #...# #.### #.#.# #.#.# #.### #.... #.... .####",
    "_": ". . . . . . . . . . ####",
    "…": ". . . . . . . . #.#.#",
    "♪": "..## ..#. ..#. ..#. ..#. .##. ###. ###. .#..",
}


def rows(ch):
    """Art as a list of equal-length strings of '#'/'.'."""
    rs = ART[ch].split()
    w = max(len(r) for r in rs)
    return [r.ljust(w, ".") for r in rs]


def width(ch):
    """Advance in pixels."""
    if ch == " ":
        return SPACE_W
    return len(rows(ch)[0]) + SPACING


def glyph(ch):
    """16x16 nibbles for the font: body F, 1 px outline E (8-neighbour), transparent 0."""
    px = [[0] * 16 for _ in range(16)]
    for y, r in enumerate(rows(ch)):
        for x, c in enumerate(r):
            if c == "#":
                px[TOP + y][1 + x] = 0xF
    for y in range(16):
        for x in range(16):
            if px[y][x] == 0 and any(px[yy][xx] == 0xF for yy in range(max(0, y - 1), min(16, y + 2))
                                     for xx in range(max(0, x - 1), min(16, x + 2))):
                px[y][x] = 0xE
    return px


def encode_en(s, string_table=False):
    """English text -> the textdb/evscript text form: every character as a `[XXXX]` Shift-JIS token, `{XXXX}`
    control codes kept. "\\n" = `{0000}` in scripts, the VWF newline code in string tables."""
    out, i = [], 0
    while i < len(s):
        # a token is exactly {XXXX} / [XXXX] with uppercase hex: "[Weak]" is text (it was sent as raw ASCII)
        if (s[i] in "{[" and i + 5 < len(s) and s[i + 5] == "}]"["{[".index(s[i])]
                and all(c in "0123456789ABCDEF" for c in s[i + 1:i + 5])):
            out.append(s[i:i + 6])
            i += 6
            continue
        c = s[i]
        if c == "\n":
            out.append("[%04X]" % NEWLINE if string_table else "{0000}")
        elif c in CODES:
            out.append("[%04X]" % CODES[c])
        elif ord(c) < 0x80:
            raise ValueError("no English glyph for %r in %r" % (c, s))
        else:
            out.append(c)  # Japanese left in place goes through cp932 as before
        i += 1
    return "".join(out)


def text_width(s):
    """Pixel width of one line of English (no control codes)."""
    return sum(width(c) for c in s)


def selftest():
    for ch in CODES:
        if ch == " ":
            continue
        assert ch in ART, "no art for %r" % ch
        rs = rows(ch)
        assert len(rs) <= 11, ch
        assert len(rs[0]) + 2 <= 16, ch
    assert len(set(CODES.values())) == len(CODES)
    assert encode_en("Hi{00C8}!\n") == "[8267][8289]{00C8}[8149]{0000}"
    assert encode_en("a\nb", True) == "[8281][81AD][8282]"


if __name__ == "__main__":
    selftest()
    if "--sheet" in sys.argv:
        for ch in sorted(ART):
            print(ch, width(ch))
            for r in glyph(ch):
                print("  " + "".join(".123456789ABCDEF"[v] for v in r))
    print("ok: %d glyphs" % len(ART))
