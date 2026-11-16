"""Title screen logo in English (docs/re/graphics.md G1, docs/decisions.md D13): redrawn at build time.

At the title the logo is 8bpp OBJs (1D mapping, the shared 256-colour OBJ palette; the art uses indices 1..63):
  plate  陰陽大戦記 + furigana strip   OBJ 9..18  tiles   0..703  resource 0x3B74F4 (0x5800 bytes)
  ribbon behind ゼロシキ              OBJ 7..8   tiles 880..903  resource 0x3BCCF4 (0x300)
  rei    零                           OBJ 0..2   tiles 780..827  resource 0x3BCFF4 (0x600)
  shiki  式                           OBJ 3..6   tiles 830..879  resource 0x3BD5F4 (0x640)
(the (pointer, size) pairs sit in the resource table at 0x403D14..). The OAM layout is built by code, so the
English stays inside the existing sprites: 陰陽大戦記 → "ONMYOU TAISENKI" (red, the kanji's own red ramp, white +
dark outline), the furigana strip → "WAR CHRONICLE" (small font), 零 → gold "ZERO" in the 零 sprites, 式 → "SHIKI"
in the 式 sprites, ゼロシキ painted out of the ribbon between them (the intro reveals 零, 式, then the ribbon, so a
word spanning the groups would show cut up). Letter masks: Anton (OFL, docs/fonts.md) rasterised once.

    python -X utf8 tools/titlelogo.py show [--orig]     # work/gfx/title_logo.png (4x, magenta = transparent)
build.py calls install(img, write).
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ensmall  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# OBJ palette indices 0..63 at the title (index 0 = transparent), from a VRAM dump of scene `title`
PAL = ("000000 403028 404040 603030 484030 703030 803028 983028 a83028 585050 b83028 904838 c83028 705848 e03028 "
       "7848b8 a85030 786830 f82828 686868 f83028 d04830 9050a0 c85030 f84028 b85858 887070 f84840 808080 988030 "
       "f85028 d86830 f86828 f06060 d08038 b88078 a078d0 989890 f88028 f87070 b8a040 f89028 b0a0c0 b0a8a8 f89088 "
       "f0a840 b8b8b8 f0a8a0 f8c848 d0c8c8 f0c0c0 e8d0a0 d8c8f0 e8d8a8 f8f048 f8e878 e0e0e0 f8f838 f8e0e0 f8f8a0 "
       "f0f0f0 f8f8d0 f8f8f8 282828").split()
RGB = [tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) for c in PAL]
I = {c: i for i, c in reversed(list(enumerate(PAL)))}     # colour -> first index

# (x, y, w, h) on screen per OBJ, in tile order
RES = {
    "plate": (0x3B74F4, [(8, 0, 64, 64), (72, 0, 64, 64), (136, 0, 64, 64), (200, 0, 32, 64), (232, 0, 16, 32),
                         (232, 32, 16, 32), (8, 64, 64, 32), (72, 64, 64, 32), (136, 64, 64, 32), (200, 64, 32, 32)]),
    "rei": (0x3BCFF4, [(62, 64, 32, 32), (94, 64, 8, 32), (62, 96, 32, 8)]),
    "shiki": (0x3BD5F4, [(120, 64, 32, 32), (152, 64, 8, 32), (120, 96, 32, 8), (152, 96, 8, 8)]),
    "ribbon": (0x3BCCF4, [(96, 72, 32, 16), (96, 88, 32, 8)]),
}
ZS = ("rei", "shiki", "ribbon")          # front to back (OAM order)
W, H = 256, 112

TITLE = """
..#####.....####.####..######....#####..####..####...#####.....###..####.........#########...######....###....#####....########..####..####..####..###..####
.#######....####.####..#######..#######.####..####..#######...####..####.........#########...######....###...#######...########..####..####..####.####..####
.########...####.####..#######..#######.####..###...########..####..####.........#########..#######....###...########..########..#####.####..####.####..####
#########...####.####..#######..#######..###..###..#########..####..####.........#########..########...###..#########..########..#####.####..####.####..####
####.####...####.####..#######..#######..###.####..####.#####.####..####.........#########..########...###..####.####..########..#####.####..####.####..####
####..####..####.####..#######..#######..###.####..####..####.####..####............###.....########...###..####.####..####......#####.####..####.###...####
####..####..#########..#######..#######..########..####..####.####..####............###.....########...###..####..###..####......#####.####..########...####
####..####..#########..#######..#######..#######...####..####.####..####............###.....########...###..#####......####......#####.####..########...####
####..####..#########..#######..#######...######...####..####.####..####............###.....########...###..#####......####......##########..########...####
####..####..#########..#######..#######...######...####..####.####..####............###.....###.####...###...#####.....########..##########..########...####
####..####..#########..#######.########...######...####..####.####..####............###.....###.####...###...######....########..##########..#######....####
####..####..#########..###########.####...######...####..####.####..####............###.....###..###...###....######...########..##########..#######....####
####..####..#########..####.######.####...#####....####..####.####..####............###.....###..###...###.....######..########..##########..########...####
####..####..#########..####.######.####...#####....####..####.####..####............###.....###..###...###......#####..########..##########..########...####
####..####..#########..####.######.####....####....####..####.####..####............###.....###..###...###.......####..####......##########..########...####
####..####..#########..####.######.####....####....####..####.####..####............###....####..###...###..####.#####.####......##########..########...####
####..####..###.#####..####.######.####....####....####..####.####..####............###....##########..###..####..####.####......####.#####..####.###...####
####..####..###.#####..####.######.####....####....####..####.####..####............###....##########..###..####..####.####......####.#####..####.####..####
####..####..###..####..####..####..####....####....####..####.####..####............###....##########..###..####..####.####......####.#####..####.####..####
####.####...###..####..####..####..####....####....####.####...####.####............###....##########..###..####.####..########..####.#####..####.####..####
#########...###..####..####..####..####....####....#########...#########............###....####..####..###..#########..########..####.#####..####.####..####
.########...###..####..####..####..####....####.....########...########.............###....####..####..###...########..########..####..####..####.####..####
.#######....###..####..####..####..####....####.....#######.....#######.............###....####..####..###...#######...########..####..####..####..####.####
..#####.....###..####..####..####..###.....####.......####.......#####..............###....####..####..###....#####....########..####..####..####..####.####
"""
# 零 -> ZERO in the 零 sprites, 式 -> SHIKI in the 式 sprites, the plain ribbon between: the intro reveals 零, then
# 式, then the ribbon, so each word must sit wholly in its own sprite group
ZERO = """
########.#######.#######.....#####..
########.#######.########...#######.
########.#######.########...#######.
########.#######.#########.#########
.#######.#######.#########.#########
....####.####....####.####.####.####
....####.###.....####.####.####.####
...####..###.....####.####.####.####
...####..###.....####.####.####.####
...####..####....####.####.####.####
...####..#######.#########.####.####
..####...#######.########..####.####
..####...#######.########..####.####
..####...#######.########..####.####
..####...#######.####.####.####.####
.####....###.....####.####.####.####
.####....###.....####.####.####.####
.####....###.....####.####.####.####
.####....###.....####.####.####.####
####.....###.....####.####.####.####
####.....####....####.####.####.####
########.#######.####.####.#########
########.#######.####.####.#########
########.#######.####.####..#######.
########.#######.####.####..#######.
########.#######.####.####...#####..
"""
SHIKI = """
..####...###..###.###.###..###.###
.######..###..###.###.###.####.###
.######..###..###.###.###.###..###
########.###..###.###.###.###..###
########.###..###.###.###.###..###
###..###.###..###.###.###.###..###
###..###.###..###.###.#######..###
###..###.###..###.###.#######..###
####.....###..###.###.######...###
#####....########.###.######...###
.####....########.###.######...###
.#####...########.###.######...###
..#####..########.###.######...###
..#####..########.###.######...###
...#####.###..###.###.######...###
....####.###..###.###.######...###
###.####.###..###.###.#######..###
###..###.###..###.###.#######..###
###..###.###..###.###.###.###..###
###..###.###..###.###.###.###..###
###..###.###..###.###.###.###..###
########.###..###.###.###.###..###
########.###..###.###.###.####.###
.######..###..###.###.###.####.###
.######..###..###.###.###..###.###
..####...###..###.###.###..###.###
"""
SUBTITLE = "WAR CHRONICLE"
GOLD = ["f8f8d0", "f8f838", "f8f838", "f8c848", "f0a840", "f89028", "f89028", "f86828", "d86830"]
DARK, WHITE, RIM = I["282828"], I["f8f8f8"], I["404040"]


def art(s):
    return [r for r in s.strip().splitlines()]


def decode8(data, objs):
    px = [[0] * W for _ in range(H)]
    t = 0
    for x0, y0, w, h in objs:
        for k in range(w * h // 64):
            ty, tx = divmod(k, w // 8)
            for y in range(8):
                for x in range(8):
                    px[y0 + ty * 8 + y][x0 + tx * 8 + x] = data[t * 64 + y * 8 + x]
            t += 1
    return px


def encode8(px, objs):
    out = bytearray()
    for x0, y0, w, h in objs:
        for k in range(w * h // 64):
            ty, tx = divmod(k, w // 8)
            for y in range(8):
                out += bytes(px[y0 + ty * 8 + y][x0 + tx * 8: x0 + tx * 8 + 8])
    return bytes(out)


def size(objs):
    return sum(w * h for _, _, w, h in objs)


def covered(objs, x, y):
    return any(ox <= x < ox + w and oy <= y < oy + h for ox, oy, w, h in objs)


def is_red(i):
    r, g, b = RGB[i]
    return r >= 0x60 and g <= 0x50 and b <= 0x48 and r > g + 0x30


def is_white(i):
    r, g, b = RGB[i]
    return (min(r, g, b) >= 0xB0 and max(r, g, b) - min(r, g, b) <= 0x48) or \
        (r >= 0xE0 and g >= 0x40 and abs(g - b) <= 0x30 and r - g >= 0x10)


def is_orange(i):
    r, g, b = RGB[i]
    return r >= 0xD0 and 0x58 <= g <= 0xA0 and b <= 0x48


def stamp(px, rows, x0, y0, fill, outline, outer):
    """Body from '#' art, 1 px `outline` ring, 1 px `outer` ring + a (1, 2) drop shadow, like the kanji."""
    body = {(x0 + x, y0 + y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "#"}
    ring = lambda s: {(x + dx, y + dy) for (x, y) in s for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    r1 = ring(body) - body
    r2 = (ring(body | r1) | {(x + 1, y + 2) for (x, y) in body | r1}) - body - r1
    for x, y in r2:
        px[y][x] = outer
    for x, y in r1:
        px[y][x] = outline
    for x, y in body:
        px[y][x] = fill((y - y0) / max(1, len(rows) - 1))


def small_text(px, text, cx, y0, ink):
    x = cx - ensmall.text_width(text) // 2
    for ch in text:
        if ch == " ":
            x += ensmall.SPACE_W
            continue
        for yy, row in enumerate(ensmall.rows(ch)):
            for xx, c in enumerate(row):
                if c == "#":
                    px[y0 + yy][x + xx] = ink
        x += ensmall.width(ch)


CX, CY = 108.5, 38.0      # the yellow diamond behind 大: manhattan rings around this centre
RING = {26: "9050a0", 27: "7848b8", 28: "a078d0", 29: "f8f8f8", 30: "585050"}


def diamond(d):
    return I[RING[d] if d in RING else "f8f838" if d <= 19 else "f0a840" if d <= 22 else "f89028"]


def draw_plate(px):
    # the kanji's red ramp, one colour per row
    ramp = {}
    for y in range(10, 53):
        c = Counter(px[y][x] for x in range(20, 182) if px[y][x] and is_red(px[y][x]))
        if c:
            ramp[y] = c.most_common(1)[0][0]
    ry = sorted(ramp)
    # clear 陰陽大戦記: rebuild the black plate and the diamond (the rope row keeps all but the kanji drips)
    for y in range(8, 53):
        for x in range(18, 187):
            i = px[y][x]
            if not i or (y >= 50 and not (is_red(i) or is_white(i) or i == DARK)):
                continue
            if x >= 178 and is_orange(i):           # the shikigami art on the right
                continue
            d = int(abs(x - CX) + abs(y - CY))
            px[y][x] = diamond(d) if d <= 30 else DARK
    for y in range(8, 50):                            # grey rim where the plate meets transparency
        for x in range(18, 187):
            if px[y][x] == DARK and int(abs(x - CX) + abs(y - CY)) > 30 and \
                    any(not px[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                px[y][x] = RIM
    # furigana strip おんみょうたいせんき -> SUBTITLE
    strip = Counter(px[55][x] for x in range(74, 144)).most_common(1)[0][0]
    for y in range(54, 60):
        for x in range(73, 145):
            px[y][x] = strip
    small_text(px, SUBTITLE, 109, 54, DARK)
    rows = art(TITLE)

    def red(t):
        y = ry[0] + 3 + t * (ry[-1] - ry[0] - 6)
        return ramp[min(ry, key=lambda r: abs(r - y))]
    stamp(px, rows, 102 - len(rows[0]) // 2, 31 - len(rows) // 2, red, WHITE, DARK)


def draw_zs(px):
    """px: the 零式 group composited front to back. Keeps only the ribbon (katakana painted over), adds ZEROSHIKI."""
    for y in range(H):
        for x in range(W):
            i = px[y][x]
            keep = 100 <= x < 124 and 74 <= y < 94 and i and RGB[i][0] > RGB[i][1] + 0x40
            if not keep:
                px[y][x] = 0
    for y in range(74, 94):                           # ゼロシキ holes -> that row's ribbon colour
        c = Counter(px[y][x] for x in range(100, 124) if px[y][x])
        if c:
            v = c.most_common(1)[0][0]
            for x in range(100, 124):
                px[y][x] = v
    gold = [I[c] for c in GOLD]
    # bodies x 64..99 (零: 62..102, its bottom-right 8x8 at y 96.. is not a sprite) and 122..157 (式: 120..160),
    # rows 67..92 so outline + shadow end by y 95
    for text, cx in ((ZERO, 82), (SHIKI, 140)):
        rows = art(text)
        stamp(px, rows, cx - len(rows[0]) // 2, 67, lambda t: gold[min(len(gold) - 1, int(t * len(gold)))],
              DARK, I["603030"])


def build(rom, orig=False):
    """{resource: new bytes} (or the original bytes with orig=True)."""
    out = {}
    off, objs = RES["plate"]
    plate = decode8(rom[off:off + size(objs)], objs)
    if not orig:
        draw_plate(plate)
    out["plate"] = encode8(plate, objs)
    layers = {n: decode8(rom[RES[n][0]:RES[n][0] + size(RES[n][1])], RES[n][1]) for n in ZS}
    comp = [[0] * W for _ in range(H)]
    for n in reversed(ZS):                             # back to front
        for y in range(H):
            for x in range(W):
                if layers[n][y][x]:
                    comp[y][x] = layers[n][y][x]
    if not orig:
        draw_zs(comp)
        for n in ZS:                                   # every sprite covering a pixel gets the composite colour
            objs = RES[n][1]
            for y in range(H):
                for x in range(W):
                    if covered(objs, x, y):
                        layers[n][y][x] = comp[y][x]
    for n in ZS:
        out[n] = encode8(layers[n], RES[n][1])
    return out


def install(img, write):
    for n, data in build(img.orig).items():
        off, objs = RES[n]
        assert len(data) == size(objs)
        write(off, data, f"title logo {n}")


def preview(rom, orig=False):
    """The logo as the title shows it (plate behind the 零式 group), RGBA, 4x."""
    from PIL import Image
    data = build(rom, orig)
    im = Image.new("RGBA", (W, H), (255, 0, 255, 255))
    for n in ("plate",) + tuple(reversed(ZS)):
        px = decode8(data[n], RES[n][1])
        for y in range(H):
            for x in range(W):
                if px[y][x] and covered(RES[n][1], x, y):
                    im.putpixel((x, y), RGB[px[y][x]] + (255,))
    return im.resize((W * 4, H * 4), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["show"])
    ap.add_argument("--orig", action="store_true")
    a = ap.parse_args()
    rom = (ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba").read_bytes()
    out = ROOT / "work" / "gfx" / f"title_logo{'_orig' if a.orig else ''}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    preview(rom, a.orig).save(out)
    print(out)


if __name__ == "__main__":
    main()
