"""List every event-script id the game's StartScript (0x0802A39C) can run, with its ROM offset and first text.

    python -X utf8 tools/script_index.py [ROM] [--tsv OUT.tsv]

StartScript(id) picks a table by id range (see docs/re/debug.md): 0..699 -> 0x41A058, 700..999 -> 0x41F848,
1000..2999 -> 0x41FE64, 3000+ -> 0x41F2D8 (id - 8000). Each entry points at a u32 that points at the script.
Empty slots point at a bare `/999` script and are skipped. Used to pick warp targets for tools/debug/scenes.txt.
"""
import argparse
import re
import struct
import sys
from pathlib import Path

ROM = Path(__file__).resolve().parent.parent / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba"
TABLES = [  # (first id, last id, table offset)
    (0, 699, 0x41A058),
    (700, 999, 0x41F848),
    (1000, 2999, 0x41FE64),
    (8000, 8999, 0x41F2D8),
]


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def ptr(d, v):
    """File offset for a ROM pointer, or None."""
    return v & 0x1FFFFFF if 0x08000000 <= v < 0x08000000 + len(d) else None


def first_text(d, off, limit=0x4000):
    """First Shift-JIS run in the script (skipping opcodes and their ASCII args)."""
    end = d.find(b"/999", off, off + limit)
    blob = d[off:end if end > 0 else off + limit]
    for m in re.finditer(rb"(?:[\x81-\x9f\xe0-\xef][\x40-\xfc])+", blob):
        if len(m.group()) >= 6:
            try:
                return m.group().decode("cp932")[:30]
            except UnicodeDecodeError:
                continue
    return ""


def scripts(d):
    for lo, hi, base in TABLES:
        for sid in range(lo, hi + 1):
            e = base + (sid - lo) * 4
            p = ptr(d, u32(d, e))
            if p is None:
                break  # past the end of this table
            q = ptr(d, u32(d, p))
            if q is None:
                break
            if d[q:q + 4] == b"/999":
                continue
            yield sid, q, d[q:q + 24].decode("latin1"), first_text(d, q)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom", nargs="?", default=str(ROM))
    ap.add_argument("--tsv")
    a = ap.parse_args()
    d = Path(a.rom).read_bytes()
    rows = list(scripts(d))
    out = open(a.tsv, "w", encoding="utf-8", newline="\n") if a.tsv else sys.stdout
    for sid, q, head, txt in rows:
        out.write(f"{sid}\t{q:06X}\t{head}\t{txt}\n")
    if a.tsv:
        out.close()
        print(f"{len(rows)} scripts -> {a.tsv}")


if __name__ == "__main__":
    main()
