"""List the visible OAM entries of a ppudump (.oam.bin), optionally only those touching a screen rect.

    python -X utf8 tools/oaminfo.py DUMP.oam.bin [--rect x,y,w,h]
Prints index, x, y, w, h, tile, palette, priority per sprite (GBA attr layout, 1D mapping assumed for tile spans).
"""
import argparse
import struct

SIZES = {(0, 0): (8, 8), (0, 1): (16, 16), (0, 2): (32, 32), (0, 3): (64, 64),
         (1, 0): (16, 8), (1, 1): (32, 8), (1, 2): (32, 16), (1, 3): (64, 32),
         (2, 0): (8, 16), (2, 1): (8, 32), (2, 2): (16, 32), (2, 3): (32, 64)}


def sprites(oam):
    for i in range(128):
        a0, a1, a2 = struct.unpack_from("<HHH", oam, i * 8)
        if (a0 >> 8) & 3 == 2:      # disabled
            continue
        w, h = SIZES.get((a0 >> 14, a1 >> 14), (0, 0))
        y, x = a0 & 0xFF, a1 & 0x1FF
        if y >= 160:
            y -= 256
        if x >= 240:
            x -= 512
        yield dict(i=i, x=x, y=y, w=w, h=h, tile=a2 & 0x3FF, pal=a2 >> 12, prio=(a2 >> 10) & 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("oam")
    ap.add_argument("--rect")
    a = ap.parse_args()
    oam = open(a.oam, "rb").read()
    r = [int(v) for v in a.rect.split(",")] if a.rect else None
    for s in sprites(oam):
        if r and not (s["x"] < r[0] + r[2] and s["x"] + s["w"] > r[0] and s["y"] < r[1] + r[3] and s["y"] + s["h"] > r[1]):
            continue
        n = s["w"] * s["h"] // 64
        print(f"#{s['i']:3} x{s['x']:4} y{s['y']:4} {s['w']}x{s['h']} tile 0x{s['tile']:03X}..0x{s['tile'] + n - 1:03X} "
              f"pal {s['pal']} prio {s['prio']}")


if __name__ == "__main__":
    main()
