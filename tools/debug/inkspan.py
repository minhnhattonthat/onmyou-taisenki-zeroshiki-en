"""Centring check for boxes on striped or gradient art, where inkbox.py's "most common colour" background fails.

    python -X utf8 tools/debug/inkspan.py SHOT.png X0,X1,Y0,Y1 [X0,X1,Y0,Y1 ...] [--min 150] [--tol 2]

X0..X1 is the inside of the box (first and last background column), Y0..Y1 the rows to scan. Text = pixels whose
every channel is above --min (the game's light lettering). Prints the left and right gap per box; exit 1 if
they differ by more than --tol, 2 if a box holds no text. Keep decorations (bolts, inner borders) out of the
scanned rows/columns, or raise --min above their colour.
"""
import argparse
import sys

from PIL import Image


def spans(path, boxes, lo):
    im = Image.open(path).convert("RGB")
    for x0, x1, y0, y1 in boxes:
        cols = [x for x in range(x0, x1 + 1) if any(min(im.getpixel((x, y))) > lo for y in range(y0, y1 + 1))]
        yield (x0, x1, y0, y1), (cols[0] - x0, x1 - cols[-1]) if cols else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("png")
    ap.add_argument("boxes", nargs="+")
    ap.add_argument("--min", type=int, default=150)
    ap.add_argument("--tol", type=int, default=2)
    a = ap.parse_args()
    rc = 0
    for box, gap in spans(a.png, [tuple(int(v) for v in b.split(",")) for b in a.boxes], a.min):
        if gap is None:
            print(f"{box}: NO TEXT")
            rc = max(rc, 2)
            continue
        bad = abs(gap[0] - gap[1]) > a.tol
        print(f"{box}: left {gap[0]} right {gap[1]}{'  OFF-CENTRE' if bad else ''}")
        rc = max(rc, int(bad))
    sys.exit(rc)


if __name__ == "__main__":
    main()
