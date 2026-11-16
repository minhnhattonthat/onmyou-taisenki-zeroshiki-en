"""Unpack every LZ77 block the scan finds into DIR/<offset hex>.bin (for vramfind.py: which block holds a tile).

    python -X utf8 tools/lzdump.py [ROM] [--out work/lz]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lzscan  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom", nargs="?", default=str(ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba"))
    ap.add_argument("--out", default=str(ROOT / "work" / "lz"))
    a = ap.parse_args()
    rom = Path(a.rom).read_bytes()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n, o = 0, 0
    while o < len(rom) - 4:
        if rom[o] == 0x10:
            r = lzscan.lz77_decompress(rom, o)
            if r:
                data, clen = r
                (out / f"{o:06X}.bin").write_bytes(data)
                n += 1
                o = (o + clen + 3) & ~3
                continue
        o += 4
    print(f"{n} blocks -> {out}")


if __name__ == "__main__":
    main()
