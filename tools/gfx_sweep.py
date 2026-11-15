"""gfx_sweep.py ROM LZ.tsv OUTDIR: static graphics-text sweep (references/graphics.md §Survey).

Renders every LZ77 block (from tools/lzscan.py) and every raw graphics region below as 4bpp tiles, 2x zoom,
32 tiles per row, into numbered sheets OUTDIR/sheet_NNN.png, with OUTDIR/index.tsv mapping each sheet row to its
source (block offset or raw offset). Blank tile rows and byte-identical blocks are dropped; every block or region
that is skipped is printed with the reason. Read-only on the ROM.
"""
import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lzscan import lz77_decompress  # noqa: E402

# Uncompressed regions that hold tile data (file table at 0x4028EC and the entropy map in docs/re/rom-map.md).
# The dialogue font 0x1B4E74-0x2247F4 (docs/re/font.md) is left out: it is the known Shift-JIS glyph set.
RAW = [(0x140000, 0x1B12D4), (0x1B12D4, 0x1B4E74), (0x2247F4, 0x25F954), (0x310000, 0x3E1254),
       (0x470000, 0x4D0000), (0x650000, 0x690000)]
print("skip raw 1b4e74-2247f4: dialogue font (known, docs/re/font.md)")
COLS, ROWS, Z = 32, 32, 2


def tile_rows(data):
    """Yield (byte_offset, 32-tile row bytes) for non-blank rows."""
    step = COLS * 32
    for o in range(0, len(data) - 31, step):
        row = data[o:o + step]
        if len(row) < 32 or not any(row) or row.count(0xFF) == len(row):
            continue
        yield o, row


def draw_row(img, y, row):
    px = img.load()
    for t in range(len(row) // 32):
        tile = row[t * 32:t * 32 + 32]
        for ty in range(8):
            for tx in range(8):
                b = tile[ty * 4 + tx // 2]
                v = (b >> 4) if tx & 1 else (b & 15)
                c = v * 17
                for dy in range(Z):
                    for dx in range(Z):
                        px[(t * 8 + tx) * Z + dx, (y * 8 + ty) * Z + dy] = c


def main():
    rom, lzlist, outdir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    outdir.mkdir(parents=True, exist_ok=True)
    d = open(rom, "rb").read()
    sources = []
    seen = set()
    for line in open(lzlist):
        off = int(line.split()[0], 16)
        r = lz77_decompress(d, off)
        if not r:
            print(f"skip lz {off:06x}: no longer decodes")
            continue
        data = r[0]
        h = hashlib.sha1(data).digest()
        if h in seen:
            print(f"skip lz {off:06x}: duplicate of an earlier block")
            continue
        seen.add(h)
        if len(data) < 256:
            print(f"skip lz {off:06x}: {len(data)} bytes (palette or tiny map)")
            continue
        sources.append((f"lz {off:06x}", data))
    for lo, hi in RAW:
        sources.append((f"raw {lo:06x}", d[lo:hi]))
    sheet, y, img = 0, 0, None
    index = open(outdir / "index.tsv", "w")
    for name, data in sources:
        for o, row in tile_rows(data):
            if img is None:
                img = Image.new("L", (COLS * 8 * Z, ROWS * 8 * Z), 40)
            draw_row(img, y, row)
            index.write(f"{sheet:03d}\t{y}\t{name}\t+{o:06x}\n")
            y += 1
            if y == ROWS:
                img.save(outdir / f"sheet_{sheet:03d}.png")
                sheet, y, img = sheet + 1, 0, None
    if img is not None:
        img.save(outdir / f"sheet_{sheet:03d}.png")
        sheet += 1
    print(f"{sheet} sheets in {outdir}")


if __name__ == "__main__":
    main()
