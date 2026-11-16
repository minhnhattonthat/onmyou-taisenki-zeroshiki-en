"""Graphics text (docs/re/graphics.md): OBJ label images redrawn in English at build time.

Each label is a run of 4bpp tiles in the ROM (raw, or inside an LZ77 block) laid out as one or more GBA sprites in
1D mapping. `decode` turns the tiles into a pixel grid of palette indices, the label's `draw` clears the Japanese
and letters the English with the game's small font art (tools/ensmall.py), and `encode` turns it back into tiles.

    python -X utf8 tools/gfx.py show NAME [--orig] [--pal DUMP.pal.bin --bank N]   # PNG in work/gfx/NAME.png
    python -X utf8 tools/gfx.py list
build.py calls install(img, write).
"""
import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import enfont  # noqa: E402
import ensmall  # noqa: E402
import lzscan  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def decode(tiles, parts):
    """tiles: 4bpp bytes; parts: [(x0, y0, w_tiles, h_tiles)] in tile order. Returns rows of indices."""
    W = max(x + w * 8 for x, y, w, h in parts)
    H = max(y + h * 8 for x, y, w, h in parts)
    px = [[0] * W for _ in range(H)]
    t = 0
    for x0, y0, w, h in parts:
        for k in range(w * h):
            ty, tx = divmod(k, w)
            for y in range(8):
                for x in range(8):
                    b = tiles[t * 32 + y * 4 + x // 2]
                    px[y0 + ty * 8 + y][x0 + tx * 8 + x] = (b >> (4 * (x & 1))) & 15
            t += 1
    return px


def encode(px, parts):
    out = bytearray()
    for x0, y0, w, h in parts:
        for k in range(w * h):
            ty, tx = divmod(k, w)
            for y in range(8):
                for x in range(0, 8, 2):
                    a = px[y0 + ty * 8 + y][x0 + tx * 8 + x]
                    b = px[y0 + ty * 8 + y][x0 + tx * 8 + x + 1]
                    out.append(a | b << 4)
    return bytes(out)


def ntiles(parts):
    return sum(w * h for _, _, w, h in parts)


def letter(px, text, x0, x1, top, ink=0xF, shadow=0xE, outline=False, font="small", drop=None, tall=False):
    """Draw text centred between x0 and x1 (exclusive), art row 0 at `top`. font: "small" (ensmall, 6 px caps,
    1 px advance gap) or "big" (enfont, the dialogue font: 9 px caps). shadow None = no shadow/outline.
    drop: a colour for a 1 px drop shadow down-right of the inked + outlined shape. tall: every font row drawn
    twice (2 px horizontal strokes, for art that is shown scaled under a scanline mask)."""
    f = ensmall if font == "small" else enfont
    gap = 1 if font == "small" else enfont.SPACING
    w = sum(f.width(c) for c in text) - gap
    x = x0 + (x1 - x0 - w) // 2
    assert x >= x0, f"gfx: {text!r} is {w} px, room {x1 - x0}"
    body = set()
    for ch in text:
        if ch != " ":
            for dy, row in enumerate(f.rows(ch)):
                for dx, c in enumerate(row):
                    if c == "#":
                        for k in ((0, 1) if tall else (0,)):
                            body.add((x + dx, top + (2 * dy + k if tall else dy)))
        x += f.width(ch)
    around = [] if shadow is None else (
        [(1, 0), (0, 1), (1, 1)] + ([(-1, 0), (0, -1), (-1, -1), (1, -1), (-1, 1)] if outline else []))
    ring = set()
    for bx, by in body:
        for dx, dy in around:
            p = (bx + dx, by + dy)
            if p not in body and 0 <= p[1] < len(px) and 0 <= p[0] < len(px[0]):
                ring.add(p)
    if drop is not None:
        for bx, by in body | ring:
            p = (bx + 1, by + 1)
            if p not in body and p not in ring and 0 <= p[1] < len(px) and 0 <= p[0] < len(px[0]):
                px[p[1]][p[0]] = drop
    for x, y in ring:
        px[y][x] = shadow
    for bx, by in body:
        px[by][bx] = ink


# --- labels ------------------------------------------------------------------------------------------------------

BUTTON = [(0, 0, 4, 2), (32, 0, 2, 2), (48, 0, 1, 2)]   # 32x16 + 16x16 + 8x16 = 56x16


def title_button(text):
    """Title menu buttons (G2, OBJ tiles 0x388.., copied by CpuSet from these 14-tile runs at f819): frame E/F/A,
    corner squares (7 in A) top-left and bottom-right, a fill striped 9/8 by row, text ink F with outline E."""
    def draw(px):
        for y in range(4, 12):
            for x in range(7, 49):
                px[y][x] = 9 if y % 2 == 0 else 8
        letter(px, text, 7, 49, 4, outline=True)
    return draw


YESNO = [(0, 0, 8, 4), (64, 0, 8, 4)]                 # two 64x32 sprites: the Yes button x 4..62, No x 63..123


def yesno_on(px, text, x0, x1):
    """Selected button (orange): fill rows 9..22 striped 5 (odd) / 4 (even) inside the 6 frame, text F outlined 3."""
    for y in range(9, 23):
        for x in range(x0, x1):
            px[y][x] = 5 if y % 2 or y == 22 else 4
    letter(px, text, x0, x1, 10, ink=0xF, shadow=3, outline=True, font="big")


def yesno_off(px, text, x0, x1):
    """Unselected button (blue B): the original engraves the text in 9 between 9 bars on every even row; English:
    bars left and right of the word, the word in 9."""
    for y in range(9, 22):
        for x in range(x0, x1):
            px[y][x] = 0xB
    w = sum(enfont.width(c) for c in text) - enfont.SPACING
    tx0 = x0 + (x1 - x0 - w) // 2
    for y in range(10, 21, 2):
        for x in list(range(x0 + 2, tx0 - 3)) + list(range(tx0 + w + 3, x1 - 2)):
            px[y][x] = 9
    letter(px, text, x0, x1, 10, ink=9, shadow=None, font="big")


def yesno(sel_yes):
    def draw(px):
        # Yes interior x 11..59 (corner square 8..10 kept), No interior x 67..115 (corner 116..118 kept)
        (yesno_on if sel_yes else yesno_off)(px, "Yes", 12, 60)
        (yesno_off if sel_yes else yesno_on)(px, "No", 67, 116)
    return draw


SPR32 = [(0, 0, 4, 4)]


def wheel(text, tall=False):
    """Battle command wheel (the Drive, OBJ tiles 0x148.. in battle, raw 0x22C434 + 0x200 k: 攻 防 逃 覧 替): one
    32x32 sprite per command, the kanji in red 4 outlined 2 with highlight 3 and a 5 drop shadow. English: the big
    font, ink 4, outline 2, drop 5, centred (caps rows 11..19).
    tall (the battle wheel): the Drive screen in the tutorial battle shows this art scaled ~1.4x under a mask that
    blanks every other scanline, which wiped out 1 px horizontal strokes ("Attack" read as "Master"); each font row
    is drawn twice instead (caps rows 6..23)."""
    def draw(px):
        for row in px:
            row[:] = [0] * len(row)
        letter(px, text, 0, 32, 6 if tall else 11, ink=4, shadow=2, outline=True, font="big", drop=5, tall=tall)
    return draw


def guard_emblem(px):
    """Guard emblem (32x32 OBJ over the 64x64 octagon when a shikigami guards; raw 0x384A8C / 0x384C8C, two
    animation frames): the kanji 防 in grey 1 with white 2 / shading 5 inside a green frame (d 2 c|b|a 2 columns).
    The interior is ~19 px wide, too narrow for "Guard" (24 px in the small font), and the message box already
    says "[Guard]": the kanji becomes a shield icon in the same colours. Interior per row: from the first frame
    pixel (a/b/c) + 2 to the last one - 3."""
    for y in range(3, 28):
        row = px[y]
        idx = [x for x, v in enumerate(row) if v in (0xA, 0xB, 0xC)]
        if not idx:
            continue
        for x in range(idx[0] + 2, idx[-1] - 2):
            row[x] = 0
    body = set()
    for dy in range(17):                 # 15 wide, straight for 10 rows, then tapering to a point
        hw = 7 if dy < 10 else 7 - (dy - 9)
        for dx in range(-hw, hw + 1):
            body.add((16 + dx, 8 + dy))
    for x, y in body:
        for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = (x + ox, y + oy)
            if p not in body:
                px[p[1]][p[0]] = 2
    for x, y in body:
        edge = any((x + ox, y + oy) not in body for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        px[y][x] = 5 if edge else 1
    for y in range(10, 22):              # a white cross on the shield
        px[y][16] = 2
    for x in range(12, 21):
        px[13][x] = 2


# 5-row bold capitals (2 px stems) for the party card labels
CARD_FONT = {
    "A": [".###.", "##.##", "#####", "##.##", "##.##"],
    "T": ["######", "..##..", "..##..", "..##..", "..##.."],
    "K": ["##.##", "####.", "###..", "####.", "##.##"],
    "P": ["####.", "##.##", "####.", "##...", "##..."],
    "O": [".###.", "##.##", "##.##", "##.##", ".###."],
    "W": ["##...##", "##.#.##", "#######", "###.###", "##...##"],
    "H": ["##..##", "##..##", "######", "##..##", "##..##"],
}


def party_card(px):
    """Party card (64x64 OBJ per party slot, lz 0x3B577C): label boxes HP / 攻 / 妖 at rows 20, 36, 52 (top border
    row), border 9, interior rows striped 8 (odd) / 9 (even), letters 5 rows tall coloured F on 8-rows and 5 on
    9-rows (an interlace look). English HP / ATK / POW (攻撃力 Attack, 妖力 Power; 3-letter stat abbreviations, as
    HP): boxes widened from x 8..25 to x 8..28 (digits start at x 35) so ATK (18 px) and POW (19 px) fit."""
    for top, text in ((20, "HP"), (36, "ATK"), (52, "POW")):
        for y in range(top, top + 7):
            for x in range(8, 29):
                edge = y in (top, top + 6) or x in (8, 28)
                px[y][x] = 9 if edge or (y - top) % 2 == 0 else 8
        w = sum(len(CARD_FONT[c][0]) for c in text) + len(text) - 1
        x = 9 + (19 - w + 1) // 2
        for c in text:
            for dy, row in enumerate(CARD_FONT[c]):
                for dx, v in enumerate(row):
                    if v == "#":
                        px[top + 1 + dy][x + dx] = 0xF if dy % 2 == 0 else 5
            x += len(CARD_FONT[c][0]) + 1


PLATE = [(0, 0, 4, 2), (32, 0, 4, 2), (64, 0, 1, 2)]   # 32x16 + 32x16 + 8x16 = 72x16


def attack_plate(text, x1=70):
    """Battle attack-tier plate (top left while the 印 panel is up; raw 0x22B6B4 + 0x240 k: 攻撃1 攻撃2 必殺技1
    必殺技2 超必殺技 超絶必殺技): frame 4/F/1/2, interior x 2..x1-1 rows 2..12 in a row gradient (1, 2 2, 3 x5,
    4 x3), text 9 outlined 4. English in the big font when it fits, else the small font. The 64x16 攻撃ボーナス
    plate (x1 = 62) is drawn the same way."""
    def draw(px):
        for y in range(2, 13):
            bg = px[y][2]
            for x in range(2, x1):
                px[y][x] = bg
        big = enfont.text_width(text) - enfont.SPACING + 2 <= x1 - 2
        letter(px, text, 2, x1, 3 if big else 4, ink=9, shadow=4, outline=True, font="big" if big else "small")
    return draw


# 7-row bold capitals for the win banner (2-unit stems)
BANNER_FONT = {
    "Y": ["##...##", "##...##", ".##.##.", "..###..", "...#...", "..###..", "..###.."],
    "O": [".#####.", "###.###", "##...##", "##...##", "##...##", "###.###", ".#####."],
    "U": ["##...##", "##...##", "##...##", "##...##", "##...##", "###.###", ".#####."],
    "W": ["##.....##", "##.....##", "##..#..##", "##.###.##", "#########", "###...###", "##.....##"],
    "I": ["######", "..##..", "..##..", "..##..", "..##..", "..##..", "######"],
    "N": ["##...##", "###..##", "####.##", "##.####", "##..###", "##...##", "##...##"],
    "!": ["##", "##", "##", "##", "##", "..", "##"],
}


def banner(text, sx=2, sy=5):
    """Battle win banner (two 64x64 OBJs, pal 9, raw 0x22D8B4 勝 at screen (6,16) and 0x22E0B4 利 at (106,48), a
    diagonal pair): each kanji has a white outline F, a dark drop shadow E down-right and a fill graded by row from
    D (top) to 1 (bottom). English "YOU" / "WIN!" on the same diagonal: BANNER_FONT scaled sx by sy, 1 px outline,
    2 px shadow, the same gradient."""
    def draw(px):
        for row in px:
            row[:] = [0] * len(row)
        w = (sum(len(BANNER_FONT[c][0]) + 1 for c in text) - 1) * sx
        x = (64 - w) // 2
        top = (64 - 7 * sy) // 2 - 1
        body = set()
        for ch in text:
            for dy, row in enumerate(BANNER_FONT[ch]):
                for dx, c in enumerate(row):
                    if c == "#":
                        body |= {(x + dx * sx + i, top + dy * sy + j) for i in range(sx) for j in range(sy)}
            x += (len(BANNER_FONT[ch][0]) + 1) * sx
        assert min(p[0] for p in body) >= 1 and max(p[0] for p in body) <= 60, f"gfx banner {text!r} too wide"
        ring = {(bx + ox, by + oy) for bx, by in body for ox in (-1, 0, 1) for oy in (-1, 0, 1)} - body
        shadow = {(x + dx, y + dy) for x, y in body | ring for dx, dy in ((1, 1), (2, 2), (1, 2), (2, 1))}
        for x, y in shadow - body - ring:
            px[y][x] = 0xE
        for x, y in ring:
            px[y][x] = 0xF
        span = 7 * sy
        for x, y in body:
            px[y][x] = max(1, 13 - (y - top) * 13 // span)
    return draw


LABELS = {
    # name: (where, offset, parts, draw)   where = "raw" (ROM offset) or "lz" (LZ77 block offset, tile offset in it)
    "title_new": ("raw", 0x224874, BUTTON, title_button("New Game")),
    "title_continue": ("raw", 0x224A34, BUTTON, title_button("Continue")),
    "title_link": ("raw", 0x224BF4, BUTTON, title_button("Link")),
    "yesno": ("lz", (0x3B4D40, 0), YESNO, yesno(False)),       # No selected (the default)
    "yesno_b": ("lz", (0x3B4FB0, 0), YESNO, yesno(True)),      # Yes selected
    # glossary b021-b026: 【攻撃】【防御】【逃げる】【一覧】【交替】 = [Attack] [Guard] [Run] [List] [Swap]
    "wheel_attack": ("raw", 0x22C434, SPR32, wheel("Attack", tall=True)),
    "wheel_guard": ("raw", 0x22C634, SPR32, wheel("Guard", tall=True)),
    "wheel_run": ("raw", 0x22C834, SPR32, wheel("Run", tall=True)),
    "wheel_list": ("raw", 0x22CA34, SPR32, wheel("List", tall=True)),
    "wheel_swap": ("raw", 0x22CC34, SPR32, wheel("Swap", tall=True)),
    # field ring menu (Start; OBJ tiles 0x000.., raw 0x3858CC + 0x200 k: 能 図 替 覧 記, same art as the wheel):
    # centre = status, left = map, left x2 = party, right x2 = shikigami list, right = save
    "ring_status": ("raw", 0x3858CC, SPR32, wheel("Status")),
    "ring_map": ("raw", 0x385ACC, SPR32, wheel("Map")),
    "ring_party": ("raw", 0x385CCC, SPR32, wheel("Party")),
    "ring_list": ("raw", 0x385ECC, SPR32, wheel("List")),
    "ring_save": ("raw", 0x3860CC, SPR32, wheel("Save")),
    "party_card": ("lz", (0x3B577C, 0), [(0, 0, 8, 8)], party_card),
    # str_system 1293B0.. uses "Special move 1" / "Super special" / "Ultimate special" in text; plates title-case
    "plate_attack1": ("raw", 0x22B6B4, PLATE, attack_plate("Attack 1")),
    "plate_attack2": ("raw", 0x22B8F4, PLATE, attack_plate("Attack 2")),
    "plate_special1": ("raw", 0x22BB34, PLATE, attack_plate("Special 1")),
    "plate_special2": ("raw", 0x22BD74, PLATE, attack_plate("Special 2")),
    "plate_super": ("raw", 0x22BFB4, PLATE, attack_plate("Super Special")),
    "plate_ultimate": ("raw", 0x22C1F4, PLATE, attack_plate("Ultimate Special")),
    # bottom left after a sealed attack, over "x 150%" (two 32x16 OBJs; the field strip shows it red, pal 15)
    "plate_bonus": ("raw", 0x3856CC, [(0, 0, 4, 2), (32, 0, 4, 2)], attack_plate("Attack Bonus", 62)),
    "guard_emblem": ("raw", 0x384A8C, SPR32, guard_emblem),
    "guard_emblem_b": ("raw", 0x384C8C, SPR32, guard_emblem),
    # battle win banner 勝利 (G6), two 64x64 OBJs on a diagonal
    "win_1": ("raw", 0x22D8B4, [(0, 0, 8, 8)], banner("YOU")),
    "win_2": ("raw", 0x22E0B4, [(0, 0, 8, 8)], banner("WIN!")),
}


def source(rom, name):
    where, off, parts, _ = LABELS[name]
    n = ntiles(parts) * 32
    if where == "raw":
        return rom[off:off + n]
    blk, toff = off
    data, _ = lzscan.lz77_decompress(rom, blk)
    return data[toff:toff + n]


def render(rom, name, orig=False):
    _, _, parts, draw = LABELS[name]
    px = decode(source(rom, name), parts)
    if not orig:
        draw(px)
    return px


def lz77_compress(data):
    """GBA BIOS LZ77 (type 0x10), greedy. Displacement >= 2 so LZ77UnCompVram (16-bit writes) decodes it too."""
    out = bytearray([0x10, len(data) & 0xFF, (len(data) >> 8) & 0xFF, (len(data) >> 16) & 0xFF])
    i = 0
    while i < len(data):
        flag_at = len(out)
        out.append(0)
        for bit in range(8):
            if i >= len(data):
                break
            best, bdisp = 0, 0
            for disp in range(2, min(i, 4096) + 1):
                n = 0
                while n < 18 and i + n < len(data) and data[i + n] == data[i + n - disp]:
                    n += 1
                if n > best:
                    best, bdisp = n, disp
                    if n == 18:
                        break
            if best >= 3:
                out[flag_at] |= 0x80 >> bit
                d = bdisp - 1
                out += bytes([((best - 3) << 4) | (d >> 8), d & 0xFF])
                i += best
            else:
                out.append(data[i])
                i += 1
    while len(out) % 4:
        out.append(0)
    return bytes(out)


# LZ blocks that may move: block offset -> the one pointer word to it (the whole ROM holds no other copy of the
# address). A block without an entry must recompress into its own room.
LZ_PTRS = {0x3B577C: 0x403CCC}     # party card: resource table entry


def install(img, write):
    rom = img.orig
    for name, (where, off, parts, _) in LABELS.items():
        new = encode(render(rom, name), parts)
        if where == "raw":
            write(off, new, f"gfx {name}")
            continue
        blk, toff = off
        data, clen = lzscan.lz77_decompress(rom, blk)
        data = data[:toff] + new + data[toff + len(new):]
        comp = lz77_compress(data)
        assert lzscan.lz77_decompress(comp, 0)[0] == data, f"gfx {name}: LZ77 roundtrip"
        if len(comp) <= clen:
            # in place: the block's pointer (or the loader's walk to the next block) stays valid
            write(blk, comp, f"gfx {name} (LZ77 in place, {len(comp)} of {clen} bytes)")
            continue
        assert blk in LZ_PTRS, f"gfx {name}: {len(comp)} bytes > room {clen} and no known pointer to move it"
        ptr = LZ_PTRS[blk]
        assert struct.unpack_from("<I", rom, ptr)[0] == 0x08000000 | blk, f"gfx {name}: pointer at {ptr:06X}"
        at = img.alloc(len(comp))
        write(at, comp, f"gfx {name} (LZ77 moved from {blk:06X}: {len(comp)} > {clen} bytes)")
        write(ptr, struct.pack("<I", 0x08000000 | at), f"gfx {name}: repoint {blk:06X} -> {at:06X}")


def png(px, path, pal=None):
    from PIL import Image
    grey = [(i * 17, i * 17, i * 17) for i in range(16)]
    pal = pal or grey
    im = Image.new("RGB", (len(px[0]), len(px)))
    for y, row in enumerate(px):
        for x, v in enumerate(row):
            im.putpixel((x, y), (255, 0, 255) if v == 0 else pal[v])
    im = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["show", "list"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("--orig", action="store_true")
    ap.add_argument("--pal")
    ap.add_argument("--bank", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "list":
        for n, (w, o, p, _) in LABELS.items():
            print(f"{n:20} {w} {o if isinstance(o, tuple) else hex(o)} {ntiles(p)} tiles")
        return
    rom = (ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba").read_bytes()
    pal = None
    if a.pal:
        raw = Path(a.pal).read_bytes()
        cols = [struct.unpack_from("<H", raw, 0x200 + a.bank * 32 + 2 * i)[0] for i in range(16)]
        pal = [((c & 31) * 8, ((c >> 5) & 31) * 8, ((c >> 10) & 31) * 8) for c in cols]
    names = [a.name] if a.name else list(LABELS)
    for n in names:
        out = ROOT / "work" / "gfx" / f"{n}{'_orig' if a.orig else ''}.png"
        png(render(rom, n, a.orig), out, pal)
        print(out)


if __name__ == "__main__":
    main()
