"""lzscan.py ROM OUT.tsv [--lo HEX --hi HEX]: find GBA BIOS LZ77 (type 0x10) blocks at 4-aligned offsets.

Recon helper (read-only). A candidate must decompress to its stated size without a back-reference before the
output start; the scan then jumps past the block (chaining back-to-back blocks). Writes start, comp_len, size.
"""
import argparse


def lz77_decompress(d, o, limit=0x80000):
    if d[o] != 0x10:
        return None
    size = d[o + 1] | d[o + 2] << 8 | d[o + 3] << 16
    if size < 0x20 or size > limit:
        return None
    out = bytearray()
    p = o + 4
    n = len(d)
    while len(out) < size:
        if p >= n:
            return None
        flags = d[p]
        p += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                if p + 1 >= n:
                    return None
                b1, b2 = d[p], d[p + 1]
                p += 2
                length = (b1 >> 4) + 3
                disp = ((b1 & 0xF) << 8 | b2) + 1
                if disp > len(out):
                    return None
                for _ in range(length):
                    out.append(out[-disp])
            else:
                if p >= n:
                    return None
                out.append(d[p])
                p += 1
    return bytes(out[:size]), p - o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("out")
    ap.add_argument("--lo", default="0")
    ap.add_argument("--hi", default="0")
    a = ap.parse_args()
    d = open(a.rom, "rb").read()
    lo, hi = int(a.lo, 16), int(a.hi, 16) or len(d)
    o = lo & ~3
    found = []
    while o < hi - 4:
        r = lz77_decompress(d, o) if d[o] == 0x10 else None
        # require at least 25% of the claimed size to be reached through compression (rules out noise)
        if r and r[1] < len(r[0]):
            found.append((o, r[1], len(r[0])))
            o = (o + r[1] + 3) & ~3
        else:
            o += 4
    with open(a.out, "w") as f:
        for s, c, n in found:
            f.write(f"{s:06x}\t{c}\t{n}\n")
    print(f"{len(found)} blocks, {sum(c for _, c, _ in found)} compressed bytes, {sum(n for *_, n in found)} out")


if __name__ == "__main__":
    main()
