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


def letter(px, text, x0, x1, top, ink=0xF, shadow=0xE, outline=False, font="small"):
    """Draw text centred between x0 and x1 (exclusive), art row 0 at `top`. font: "small" (ensmall, 6 px caps,
    1 px advance gap) or "big" (enfont, the dialogue font: 9 px caps). shadow None = no shadow/outline."""
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
                        body.add((x + dx, top + dy))
        x += f.width(ch)
    around = [] if shadow is None else (
        [(1, 0), (0, 1), (1, 1)] + ([(-1, 0), (0, -1), (-1, -1), (1, -1), (-1, 1)] if outline else []))
    for bx, by in body:
        for dx, dy in around:
            p = (bx + dx, by + dy)
            if p not in body and 0 <= p[1] < len(px) and 0 <= p[0] < len(px[0]):
                px[p[1]][p[0]] = shadow
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


LABELS = {
    # name: (where, offset, parts, draw)   where = "raw" (ROM offset) or "lz" (LZ77 block offset, tile offset in it)
    "title_new": ("raw", 0x224874, BUTTON, title_button("New Game")),
    "title_continue": ("raw", 0x224A34, BUTTON, title_button("Continue")),
    "title_link": ("raw", 0x224BF4, BUTTON, title_button("Link")),
    "yesno": ("lz", (0x3B4D40, 0), YESNO, yesno(False)),       # No selected (the default)
    "yesno_b": ("lz", (0x3B4FB0, 0), YESNO, yesno(True)),      # Yes selected
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
        # in place: the block's pointer (or the loader's walk to the next block) stays valid
        assert len(comp) <= clen, f"gfx {name}: {len(comp)} bytes > room {clen}"
        write(blk, comp, f"gfx {name} (LZ77 in place, {len(comp)} of {clen} bytes)")


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
