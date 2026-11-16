"""Town shop signs (graphics survey G11): field tileset art redrawn in English at build time.

The town tilesets are LZ77 blocks behind the pointer table 0x0858D190 (entries 0..19; each pointer is to a 4-byte
header, the LZ77 data starts 4 bytes later), loaded by 0x080089D4(idx, slot) into BG char base 0x8000, so a VRAM
tile number = tile index in the block. A sign is a grid of tiles from one block; `redraw` blanks the lettering in
its box (each row back to that row's most common colour) and letters the English with the game's fonts
(gfx.letter). The changed tiles are then swapped wherever the same 32 bytes occur in any town tileset, so a sign
that several tilesets share (in other awning colours = other palettes) changes everywhere at once.

    python -X utf8 tools/signs.py show NAME --dump work/qa/g11/p021/ppu_000029 --pal 11   # work/gfx/sign_NAME.png
    python -X utf8 tools/signs.py list

Find a sign's tiles from a ppudump of its map: every town map fits in the 512x512 BG2/BG3 maps, so the whole map
is in VRAM (docs/re/graphics.md G11). Illegible lettering (the blue post plates, the bath-house brush plate) is
left as it is (D5: translate the readable ones).
"""
import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gfx  # noqa: E402
import lzscan  # noqa: E402

TABLE = 0x58D190
TOWN = range(20)


def block(rom, idx):
    """(header offset, LZ77 offset, decompressed bytes, compressed length) of town tileset idx."""
    hdr = struct.unpack_from("<I", rom, TABLE + 4 * idx)[0] & 0x1FFFFFF
    data, clen = lzscan.lz77_decompress(rom, hdr + 4)
    return hdr, hdr + 4, data, clen


def tile(data, t):
    return data[t * 32:t * 32 + 32]


def decode(data, grid):
    """grid: rows of tile indices (None = blank). Returns rows of colour indices."""
    px = [[0] * (8 * len(grid[0])) for _ in range(8 * len(grid))]
    for ty, row in enumerate(grid):
        for tx, t in enumerate(row):
            if t is None:
                continue
            b = tile(data, t)
            for y in range(8):
                for x in range(8):
                    px[ty * 8 + y][tx * 8 + x] = (b[y * 4 + x // 2] >> (4 * (x & 1))) & 15
    return px


def encode_tile(px, tx, ty):
    out = bytearray()
    for y in range(8):
        for x in range(0, 8, 2):
            out.append(px[ty * 8 + y][tx * 8 + x] | px[ty * 8 + y][tx * 8 + x + 1] << 4)
    return bytes(out)


def mode(vals):
    return max(set(vals), key=vals.count)


# 3x5 caps for the signs whose lettering room is narrower than the small font (6 px caps, 4 px wide)
MICRO = {
    "A": ".#.|#.#|###|#.#|#.#", "B": "##.|#.#|##.|#.#|##.", "C": ".##|#..|#..|#..|.##", "D": "##.|#.#|#.#|#.#|##.",
    "E": "###|#..|##.|#..|###", "F": "###|#..|##.|#..|#..", "G": ".##|#..|#.#|#.#|.##", "H": "#.#|#.#|###|#.#|#.#",
    "I": "###|.#.|.#.|.#.|###", "K": "#.#|#.#|##.|#.#|#.#", "L": "#..|#..|#..|#..|###", "M": "#.#|###|###|#.#|#.#",
    "N": "##.|#.#|#.#|#.#|#.#", "O": ".#.|#.#|#.#|#.#|.#.", "P": "##.|#.#|##.|#..|#..", "R": "##.|#.#|##.|#.#|#.#",
    "S": ".##|#..|.#.|..#|##.", "T": "###|.#.|.#.|.#.|.#.", "U": "#.#|#.#|#.#|#.#|###", "V": "#.#|#.#|#.#|#.#|.#.", "W": "#.#|#.#|###|###|#.#",
    "Y": "#.#|#.#|.#.|.#.|.#.",
}


def micro(px, text, x0, x1, top, ink):
    w = 4 * len(text) - 1
    x = x0 + (x1 - x0 - w) // 2
    assert x >= x0, f"signs: {text!r} is {w} px, room {x1 - x0}"
    for ch in text:
        if ch != " ":
            for dy, row in enumerate(MICRO[ch].split("|")):
                for dx, c in enumerate(row):
                    if c == "#":
                        px[top + dy][x + dx] = ink
        x += 4


def blank(px, box, cols):
    """Remove the lettering: every pixel of box whose colour is in `cols` becomes its row's background, the most
    common other colour among the row's pixels of the same column parity (so 2-px dither rows stay dithered); a row
    with nothing else takes the row above's."""
    x0, y0, x1, y1 = box
    bg = None
    for y in range(y0, y1):
        new = []
        for k in (0, 1):
            rest = [v for v in px[y][x0 + k:x1:2] if v not in cols]
            new.append(mode(rest) if rest else (bg[k] if bg else None))
        bg = new
        for x in range(x0, x1):
            if px[y][x] in cols:
                px[y][x] = bg[(x - x0) & 1]


def redraw(px, text, box, font="small", ink=None, shadow=None, top=None, cols=None, lines=None, drop=None):
    """Remove the lettering colours `cols` (default: ink and shadow) from box (x0, y0, x1, y1) (see blank), then
    letter `text` centred in it. top None = vertically centred. lines: several texts, one per line.
    font: "small" (6 px caps), "big" (9 px caps) or "micro" (3x5, no shadow)."""
    x0, y0, x1, y1 = box
    blank(px, box, cols if cols is not None else {ink, shadow} - {None})
    lines = lines or [text]
    h = {"small": 6, "big": 9, "micro": 5}[font]
    gap = 2
    total = len(lines) * h + (len(lines) - 1) * gap
    t = y0 + (y1 - y0 - total) // 2 if top is None else top
    for k, line in enumerate(lines):
        if font == "micro":
            micro(px, line, x0, x1, t + k * (h + gap), ink)
        else:
            gfx.letter(px, line, x0, x1, t + k * (h + gap), ink=ink, shadow=shadow, font=font, drop=drop)


# name: (tileset idx, tile grid, draw(px)). Grids come from signloc ppudumps of the map named in the comment.
SIGNS = {
    # map 21 (idx 8): green awning クリーニング, text in tiles 195..199 (194/193 repeat at the ends)
    "cleaning": (8, [[0x193, 0x194, 0x195, 0x196, 0x197, 0x198, 0x199, 0x194]],
                 lambda px: redraw(px, "CLEANING", (16, 0, 56, 7), ink=6, shadow=0xF, top=0)),
    # map 67 (idx 16, pal B): blue awning クリーニング
    "cleaning_b": (16, [[0x16C, 0x16D, 0x16D, 0x16E, 0x16F, 0x170, 0x171, 0x172, 0x16D, 0x16D]],
                   lambda px: redraw(px, "CLEANING", (24, 0, 64, 7), ink=6, top=0, cols={6, 7})),
    # map 29 (idx 11, pal D): orange awning 来々軒 (a ramen shop name); lettering in tiles 100..103 / 113..116
    "ramen": (11, [[0x0FE, 0x0FF, 0x0FF, 0x100, 0x101, 0x102, 0x103, 0x0FF, 0x0FF],
                   [0x111, 0x112, 0x112, 0x113, 0x114, 0x115, 0x116, 0x112, 0x112]],
              lambda px: redraw(px, "RAMEN", (24, 3, 56, 16), font="big", ink=2, top=4)),
    # map 31 (idx 11, pal C): yellow banner 薬 (pharmacy); only tiles 1D0/1D1/1D6/1D7 (16 px) are free of the stripes
    "drugs": (11, [[0x1CE, 0x1CF, 0x1CF, 0x1CF, 0x1CF, 0x1D0, 0x1D1, 0x1CF, 0x1CF],
                   [0x1D4, 0x1D5, 0x1D5, 0x1D5, 0x1D5, 0x1D6, 0x1D7, 0x1D5, 0x1D5]],
              lambda px: redraw(px, "DRUG", (40, 3, 56, 15), font="micro", ink=1, top=4)),
    # map 60 (idx 14, pal D): DVD ビデオ panel; the katakana sit in x 43..61 beside the red "DVD"
    "video": (14, [[0x0D5, 0x0D6, 0x0D7, 0x0D7, 0x0D7, 0x0D7, 0x0D7, 0x0D8, 0x0D9],
                   [0x0EC, 0x0ED, 0x0EE, 0x0EF, 0x0F0, 0x0F1, 0x0F2, 0x0F3, 0x0F4],
                   [0x104, 0x105, 0x106, 0x106, 0x106, 0x106, 0x106, 0x107, 0x108]],
              lambda px: redraw(px, "VIDEO", (42, 8, 62, 16), font="micro", ink=7, top=9)),
    # map 62 (idx 14, pal B): faint awning lettering 八百長 (a pun on 八百屋, greengrocer), see grocer()
    "grocer": (14, [[0x188, 0x189, 0x18A, 0x18B, 0x189, 0x18C, 0x18D, 0x189, 0x18E, 0x18F, 0x189, 0x188],
                    [0x194, 0x195, 0x196, 0x197, 0x198, 0x199, 0x19A, 0x198, 0x19B, 0x19C, 0x19D, 0x194]],
               lambda px: grocer(px)),
    # map 66 (idx 15, pal B): blue strip アパート・マンション, 5 px lettering (F, shade E)
    "apartments": (15, [[0x1B8, 0x1B9, 0x1BA, 0x1BB, 0x1BC, 0x1BD, 0x1BE, 0x1BF, 0x1C0, 0x1C0]],
                   lambda px: redraw(px, "APARTMENTS", (8, 2, 64, 7), font="micro", ink=0xF, top=2, cols={0xE, 0xF})),
    # map 65 (idx 15, pal E): green awning 花; only tiles 107/108/111/112 (x 24..39) are its own
    "flowers": (15, [[0x0FC, 0x0FD, 0x0FD, 0x0FD, 0x0FD], [0x105, 0x106, 0x106, 0x107, 0x108],
                     [0x10F, 0x110, 0x110, 0x111, 0x112]],
                lambda px: redraw(px, "", (24, 10, 40, 23), font="micro", ink=6, top=11, cols={6, 0xE},
                                  lines=["FLOW", "ERS"])),
    # map 60 (idx 14, pal B): purple awning クリーニング
    "cleaning_p": (14, [[0x192, 0x193, 0x193, 0x193, 0x193, 0x193, 0x193, 0x193],
                        [0x1A0, 0x1A1, 0x1A2, 0x1A3, 0x1A4, 0x1A5, 0x1A6, 0x1A1]],
                   lambda px: redraw(px, "CLEANING", (16, 8, 56, 15), ink=7, shadow=0xF, top=8, cols={7, 0xF})),
    # map 66 (idx 15, BG3 pal E, x 120 y 176): vertical green sign 京中銀行 (Kyonaka Bank); 銀行 is drawn faded
    # (colour 7 in a hatched lower half), so the English does the same: B A clear, N K faded
    "bank": (15, [[0x1AB, 0x1AC], [0x1AD, 0x1AE], [0x1B2, 0x1B3], [0x1C1, 0x1C2], [0x1CD, 0x1CE]],
             lambda px: (redraw(px, "", (1, 2, 15, 23), ink=6, cols={6}, lines=["B", "A"], top=5),
                         redraw(px, "", (1, 23, 15, 39), ink=7, cols={7}, lines=["N", "K"], top=24))),
    # map 66 (idx 15, pal C): long yellow banner 薬; its kanji tiles 1E1/1E2/1E5/1E6 (x 16..31) differ from idx 11's
    "drugs15": (15, [[0x1DF, 0x1E0, 0x1E1, 0x1E2, 0x1E0], [0x1E3, 0x1E4, 0x1E5, 0x1E6, 0x1E4]],
                lambda px: redraw(px, "DRUG", (16, 3, 32, 15), font="micro", ink=1, top=4)),
    # map 68 (idx 16, pal D): yellow plate 牛丼 (beef bowl) on the red awning, 22 x 7 px
    "gyudon": (16, [[0x1D5, 0x1D6, 0x1D7, 0x1D4]],
               lambda px: redraw(px, "BEEF", (1, 0, 23, 7), font="micro", ink=2, top=1)),
    # map 67 (idx 16, pal E): green plate 京中歯科医院 (Kyonaka Dental Clinic)
    "dental": (16, [[0x06E, 0x06F, 0x06F, 0x06F, 0x06F, 0x06F, 0x06F, 0x06F, 0x070, 0x071],
                    [0x088, 0x089, 0x08A, 0x08B, 0x08C, 0x08D, 0x08E, 0x08F, 0x090, None]],
               lambda px: redraw(px, "DENTIST", (12, 8, 62, 15), ink=6, top=8, cols={6})),
}


def grocer(px):
    """八百長 sits in the three 16-px slots between the awning's repeated tiles (x 16, 40, 64): one big letter per
    slot, coloured per awning band like the original (band E -> 9, D -> 8, C -> 7)."""
    band = {y: 9 for y in (1, 2)} | {y: 8 for y in range(3, 8)} | {y: 7 for y in range(8, 13)} | {13: 8, 14: 8}
    blank(px, (8, 8, 16, 16), {7, 8, 9})    # 八 and 長 spill into the unique bottom edge tiles 195 / 19D
    blank(px, (80, 8, 88, 16), {7, 8, 9})
    for x0, ch in zip((16, 40, 64), "VEG"):
        blank(px, (x0, 0, x0 + 16, 16), {7, 8, 9})
        gfx.letter(px, ch, x0, x0 + 15, 3, ink=0x10, shadow=0x10, font="big")  # shadow in ink = 2 px strokes
    for y, row in enumerate(px):
        for x, v in enumerate(row):
            if v == 0x10:
                row[x] = band[y]


def changes(rom):
    """{original tile bytes: new tile bytes} over every sign."""
    out = {}
    for name, (idx, grid, draw) in SIGNS.items():
        data = block(rom, idx)[2]
        px = decode(data, grid)
        draw(px)
        new = {}
        for ty, row in enumerate(grid):
            for tx, t in enumerate(row):
                if t is None:
                    continue
                b = encode_tile(px, tx, ty)
                assert new.setdefault(t, b) == b, f"sign {name}: tile {t:X} is used twice and drawn differently"
        for t, b in new.items():
            old = tile(data, t)
            if b != old:
                assert out.setdefault(old, b) == b, f"sign {name}: tile {t:X} also changed by another sign"
    return out


def install(img, write):
    """Swap the changed tiles in every town tileset; recompress in place, or move the block and repoint the table."""
    rom = img.orig
    swap = changes(rom)
    for idx in TOWN:
        hdr, lz, data, clen = block(rom, idx)
        new = bytearray(data)
        hits = 0
        for t in range(len(data) // 32):
            b = swap.get(tile(data, t))
            if b:
                new[t * 32:t * 32 + 32] = b
                hits += 1
        if not hits:
            continue
        comp = gfx.lz77_compress(bytes(new))
        assert lzscan.lz77_decompress(comp, 0)[0] == bytes(new), f"signs: tileset {idx} LZ77 roundtrip"
        room = struct.unpack_from("<I", rom, TABLE + 4 * idx + 4)[0] - 0x08000000 - lz
        if len(comp) <= room:
            write(lz, comp, f"sign tiles: tileset {idx} ({hits} tiles, LZ77 in place {len(comp)} of {room})")
            continue
        at = img.alloc(4 + len(comp))
        write(at, rom[hdr:hdr + 4] + comp, f"sign tiles: tileset {idx} ({hits} tiles, moved: {len(comp)} > {room})")
        write(TABLE + 4 * idx, struct.pack("<I", 0x08000000 | at), f"sign tiles: repoint tileset {idx}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["show", "list"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("--dump", help="ppudump prefix for the palette")
    ap.add_argument("--pal", type=int, default=0, help="BG palette bank")
    ap.add_argument("--grid", action="store_true", help="also print the colour indices")
    a = ap.parse_args()
    rom = (ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba").read_bytes()
    if a.cmd == "list":
        for name, (idx, grid, _) in SIGNS.items():
            print(f"{name:14} tileset {idx:2}  {len(grid[0])}x{len(grid)} tiles")
        return
    idx, grid, draw = SIGNS[a.name]
    data = block(rom, idx)[2]
    pal = None
    if a.dump:
        raw = Path(a.dump + ".pal.bin").read_bytes()
        pal = []
        for i in range(16):
            c = struct.unpack_from("<H", raw, (a.pal * 16 + i) * 2)[0]
            pal.append(((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3))
    before = decode(data, grid)
    if a.grid:
        for row in before:
            print("".join(f"{v:X}" for v in row))
    after = decode(data, grid)
    draw(after)
    both = before + [[0] * len(before[0])] * 2 + after
    out = ROOT / "work" / "gfx" / f"sign_{a.name}.png"
    gfx.png(both, out, pal)
    print(out)


if __name__ == "__main__":
    main()
