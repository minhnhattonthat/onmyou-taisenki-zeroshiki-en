"""BG tilemap entries of a ppudump (emu.py + ppudump.lua: PREFIX.vram.bin / .io.bin) for a screen rectangle.

    python -X utf8 tools/bgmap.py work/qa/x/ppu_013021 --rect 0,32,80,16 [--bg 0,1,2,3]

Text-mode BGs only (mode 0, or BG0/1 in modes 1/2). Prints per enabled BG: priority, char base, map base, then the
rows of `tile:pal` entries (h/v flip as h/v) and the VRAM byte range of every tile used, for vramfind.py --lo/--hi.
"""
import argparse
import struct


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prefix")
    ap.add_argument("--rect", default="0,0,240,160")
    ap.add_argument("--bg", default="0,1,2,3")
    ap.add_argument("--scroll", type=int, default=1, help="0 = ignore the dumped scroll registers")
    a = ap.parse_args()
    vram = open(a.prefix + ".vram.bin", "rb").read()
    io = open(a.prefix + ".io.bin", "rb").read()
    x, y, w, h = (int(v) for v in a.rect.split(","))
    disp = struct.unpack_from("<H", io, 0)[0]
    print(f"DISPCNT {disp:04X} mode {disp & 7}")
    for bg in (int(b) for b in a.bg.split(",")):
        if not disp & (0x100 << bg):
            continue
        cnt = struct.unpack_from("<H", io, 8 + 2 * bg)[0]
        # BGnHOFS/VOFS are write-only: a dump may hold junk there (--scroll 0 ignores it)
        hofs = struct.unpack_from("<H", io, 0x10 + 4 * bg)[0] & 0x1FF if a.scroll else 0
        vofs = struct.unpack_from("<H", io, 0x12 + 4 * bg)[0] & 0x1FF if a.scroll else 0
        char, smap, bpp8, size = (cnt >> 2) & 3, (cnt >> 8) & 31, cnt >> 7 & 1, cnt >> 14
        mw, mh = (32, 64, 32, 64)[size], (32, 32, 64, 64)[size]
        print(f"BG{bg} cnt {cnt:04X} prio {cnt & 3} char 0x{char * 0x4000:05X} map 0x{smap * 0x800:05X} "
              f"{'8' if bpp8 else '4'}bpp scroll {hofs},{vofs}")
        tiles = set()
        for ty in range((y + vofs) // 8, (y + h + vofs + 7) // 8):
            row = []
            for tx in range((x + hofs) // 8, (x + w + hofs + 7) // 8):
                mx, my = tx % mw, ty % mh
                blk = (mx // 32) + (my // 32) * (2 if mw == 64 else 1)
                e = struct.unpack_from("<H", vram, smap * 0x800 + blk * 0x800 + ((my % 32) * 32 + mx % 32) * 2)[0]
                t = e & 0x3FF
                tiles.add(t)
                row.append(f"{t:03X}:{e >> 12:X}{'h' if e & 0x400 else ''}{'v' if e & 0x800 else ''}")
            print("  " + " ".join(row))
        size_t = 64 if bpp8 else 32
        for t in sorted(tiles):
            lo = char * 0x4000 + t * size_t
            print(f"  tile {t:03X} vram {lo:05X}-{lo + size_t - 1:05X}")


if __name__ == "__main__":
    main()
