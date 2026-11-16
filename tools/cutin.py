"""Battle super-move cut-in (graphics survey G5): the technique name drops in as a column of 32x32 OBJ cells.

How the original draws it (docs/re/graphics.md "Super-move cut-in"): 0x081096EA takes the name from techniques_b
(table 0x0813BD78, one word per shikigami id 0..75) and 0x08109614 matches each 2-byte char against the 380 one-kanji
key strings at 0x0840E56C (str_battle_kanji); the key's index k is the graphic index of resource type 0x27, loaded by
0x0800509C(0x27, k, dst): index array + 12-byte descriptors from table 0x08403DA4 (type 0x27: 375 indices), art base
and size from table 0x084028EC (type 0x27: raw 0x2320B4, 0x20000 bytes = 256 kanji cells). The cell count is 5, 4
for ids 72/73 and 3 for id 74 (0x081096C6).

The English version keeps all that code and replaces the data:
  - each distinct name gets its own cells (371 of the 375 indices), its English drawn rotated 90 degrees clockwise
    (read top to bottom) across them in the original's style: fill ramp 1..13 down each cell, outline 15, drop 14;
  - the cut-in's copy of techniques_b (literal 0x0810971C) points at strings of 2-byte codes, one per cell, and the
    first 375 key pointers point at those codes, so key k = cell k;
  - new art, index array and descriptors in free space; the two type-0x27 table entries repointed.
str_battle_kanji (the old keys) is then read by nothing: waived in docs/text_unshown.tsv.

    python -X utf8 tools/cutin.py show [ID ..]     # work/gfx/cutin.png: the columns as the game shows them
"""
import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ensmall  # noqa: E402

NAMES = 0x13BD78      # techniques_b pointer table (76 ids)
IDS = 76
LIT = 0x10971C        # the cut-in's literal for NAMES
KEYS = 0x40E56C       # 380 key string pointers (str_battle_kanji)
NKEYS = 380
RES_IDX = 0x403DA4    # per resource type: (index array, descriptors)
RES_BASE = 0x4028EC   # per resource type: (art base, size)
TYPE = 0x27
NCELLS = 375
CELL = 0x200
SCALE = 2             # small font doubled: 12 px caps


def ncells(sid):
    return 4 if sid in (72, 73) else 3 if sid == 74 else 5


def code(k):
    """The 2-byte key that selects cell k (no NUL byte, unique)."""
    return bytes([0xE0 + k // 128, 0x80 + k % 128])


def english():
    """{original string offset: English} for techniques_b."""
    d = json.loads((ROOT / "script" / "str_techniques_b.json").read_text(encoding="utf-8"))
    return {int(e["id"], 16): e["en"] for e in d["entries"]}


def name_ptrs(orig):
    return [struct.unpack_from("<I", orig, NAMES + 4 * i)[0] - 0x08000000 for i in range(IDS)]


def adv(c, tight):
    """Advance of c at SCALE: the glyph doubled, then the 1 px gap doubled (or kept at 1 px when tight)."""
    return SCALE * ensmall.width(c) - (1 if tight and c != " " else 0)


def text_w(s, tight=False):
    return sum(adv(c, tight) for c in s) - (SCALE - (1 if tight else 0))


def lines_for(text, room):
    """(lines, tight): one line if it fits `room` px, else the most balanced split into two at a space; letter gaps
    tightened to 1 px only when the normal ones don't fit."""
    text = text.upper()
    for tight in (False, True):
        if text_w(text, tight) <= room:
            return [text], tight
        cuts = [(i, i + 1) for i, c in enumerate(text) if c == " "] + [(i + 1, i + 1) for i, c in enumerate(text)
                                                                         if c == "-"]
        best = None
        for e, s in cuts:   # line 1 = text[:e], line 2 = text[s:] (a space is dropped, a hyphen stays on line 1)
            a, b = text[:e], text[s:]
            w = max(text_w(a, tight), text_w(b, tight))
            if w <= room and (best is None or w < best[0]):
                best = (w, [a, b])
        if best:
            return best[1], tight
    raise AssertionError(f"cutin: {text!r} does not fit {room} px in two lines")


def column(text, n):
    """The name as the game shows it: 32 px wide, 32n tall, colour indices (0 = clear)."""
    L = 32 * n
    lines, tight = lines_for(text, L - 2)
    lh = 6 * SCALE
    gap = 2
    total = len(lines) * lh + (len(lines) - 1) * gap
    top = (32 - total) // 2
    body = set()   # horizontal canvas: x along the name (0..L), y across (0..32)
    for i, line in enumerate(lines):
        x = (L - text_w(line, tight)) // 2
        y0 = top + i * (lh + gap)
        for ch in line:
            if ch != " ":
                for dy, row in enumerate(ensmall.rows(ch)):
                    for dx, c in enumerate(row):
                        if c == "#":
                            for sx in range(SCALE):
                                for sy in range(SCALE):
                                    body.add((x + dx * SCALE + sx, y0 + dy * SCALE + sy))
            x += adv(ch, tight)
    # rotate 90 degrees clockwise: canvas (x, y) -> column (31 - y, x), so the text reads top to bottom
    rot = {(31 - y, x) for x, y in body}
    px = [[0] * 32 for _ in range(L)]
    ring = set()
    for x, y in rot:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (x + dx, y + dy)
                if p not in rot and 0 <= p[0] < 32 and 0 <= p[1] < L:
                    ring.add(p)
    for x, y in rot | ring:
        p = (x + 1, y + 1)
        if p not in rot and p not in ring and p[0] < 32 and p[1] < L:
            px[p[1]][p[0]] = 14
    for x, y in ring:
        px[y][x] = 15
    for x, y in rot:
        px[y][x] = min(13, 1 + (y % 32 - 2) * 13 // 28) if y % 32 >= 2 else 1
    return px


def encode_cell(px, k):
    """Cell k (rows 32k..32k+31) of a column as one 32x32 OBJ: 16 tiles in 1D order (4 across, 4 down)."""
    out = bytearray()
    for t in range(16):
        tx, ty = t % 4, t // 4
        for y in range(8):
            row = px[32 * k + ty * 8 + y]
            for x in range(0, 8, 2):
                out.append(row[tx * 8 + x] | row[tx * 8 + x + 1] << 4)
    return bytes(out)


def plan(orig):
    """[(id, name offset, English, first cell, cells)] per distinct name, in id order."""
    en = english()
    out, seen, nxt = [], {}, 0
    for sid, p in enumerate(name_ptrs(orig)):
        if p in seen:
            continue
        n = ncells(sid)
        seen[p] = nxt
        out.append((sid, p, en[p], nxt, n))
        nxt += n
    assert nxt <= NCELLS, f"cutin: {nxt} cells > {NCELLS}"
    return out, seen


def install_names(img, write):
    """The cut-in's name table: per id, the codes of its cells. Allocated where build.py used to put the JP copy of
    techniques_b, with the same size (a 5-kanji name + NUL + pad = 12 bytes = 5 codes + 2), so nothing after it
    moves."""
    orig = img.orig
    names, _ = plan(orig)
    strs, at = bytearray(), {}
    for sid, p, text, k0, n in names:
        at[p] = len(strs)
        strs += b"".join(code(k0 + k) for k in range(n)) + b"\0\0"
        jp = orig.index(b"\0", p) + 1 - p
        assert len(strs) - at[p] == jp + jp % 2, f"cutin: id {sid} codes size differs from the JP copy"
    at_tab = img.alloc(4 * IDS + len(strs))
    base = at_tab + 4 * IDS
    write(at_tab, b"".join(struct.pack("<I", 0x08000000 | (base + at[p])) for p in name_ptrs(orig)) + bytes(strs),
          "cutin: name codes table")
    write(LIT, struct.pack("<I", 0x08000000 | at_tab), "cutin: literal -> name codes table")


def install(img, write):
    """Art, index array, descriptors, keys (after the text: allocations here move no string)."""
    orig = img.orig
    names, first = plan(orig)
    art = bytearray(NCELLS * CELL)
    for sid, p, text, k0, n in names:
        px = column(text, n)
        for k in range(n):
            art[(k0 + k) * CELL:(k0 + k + 1) * CELL] = encode_cell(px, k)
    # index array (header as the original: type, count, 32 x 32) + descriptors (1 part, 0x200 bytes, at -16,-16)
    a_old = struct.unpack_from("<I", orig, RES_IDX + 8 * TYPE)[0] - 0x08000000
    assert orig[a_old:a_old + 8] == bytes([TYPE, 0, NCELLS & 0xFF, NCELLS >> 8, 32, 0, 32, 0])
    # after the indices: the attribute list (count 1, entry 39 = 16-colour palette 3), read by 0x0800B310 at
    # array + 2 * count + 10; without it the cells come out as 256-colour OBJs
    tail = orig[a_old + 8 + 2 * NCELLS:a_old + 12 + 2 * NCELLS]
    assert tail == struct.pack("<HH", 1, 39), tail.hex()
    idx = orig[a_old:a_old + 8] + b"".join(struct.pack("<H", 6 * k) for k in range(NCELLS)) + tail
    desc = b"".join(struct.pack("<HHhhHH", 1, CELL, -16, -16, 0x8000 | (k * CELL) >> 16, (k * CELL) & 0xFFFF)
                    for k in range(NCELLS))
    at_art = img.alloc(len(art))
    write(at_art, bytes(art), "cutin: name art (375 cells)")
    at_idx = img.alloc(len(idx))
    write(at_idx, idx, "cutin: type 0x27 index array")
    at_desc = img.alloc(len(desc))
    write(at_desc, desc, "cutin: type 0x27 descriptors")
    write(RES_IDX + 8 * TYPE, struct.pack("<II", 0x08000000 | at_idx, 0x08000000 | at_desc), "cutin: index table")
    write(RES_BASE + 8 * TYPE, struct.pack("<II", 0x08000000 | at_art, len(art)), "cutin: art base + size")
    # keys: key k = code(k); the cut-in's name table: per id, the codes of its cells
    keys = b"".join(code(k) + b"\0\0" for k in range(NCELLS))
    at_keys = img.alloc(len(keys))
    write(at_keys, keys, "cutin: key codes")
    write(KEYS, b"".join(struct.pack("<I", 0x08000000 | (at_keys + 4 * k)) for k in range(NCELLS)),
          "cutin: key pointers 0..374")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["show"])
    ap.add_argument("ids", nargs="*", type=int)
    a = ap.parse_args()
    from PIL import Image
    orig = (ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba").read_bytes()
    names, _ = plan(orig)
    if a.ids:
        names = [x for x in names if x[0] in a.ids]
    pal = [(0, 0, 0)] + [(255, 40 + 12 * i, 40) for i in range(13)] + [(90, 0, 0), (255, 255, 255)]
    Z = 2
    im = Image.new("RGB", (len(names) * 36 * Z, 160 * Z), (30, 30, 60))
    for i, (sid, p, text, k0, n) in enumerate(names):
        px = column(text, n)
        for y, row in enumerate(px):
            for x, v in enumerate(row):
                if v:
                    im.paste(pal[v], ((i * 36 + x) * Z, y * Z, (i * 36 + x + 1) * Z, (y + 1) * Z))
    out = ROOT / "work" / "gfx" / "cutin.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(out, len(names), "names")


if __name__ == "__main__":
    main()
