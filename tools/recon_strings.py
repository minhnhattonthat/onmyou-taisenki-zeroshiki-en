"""recon_strings.py ROM OUT.tsv: map NUL-terminated Shift-JIS strings to the aligned u32 pointers that reach them.

Recon helper (read-only). A string = a run starting with a Shift-JIS lead byte (or fullwidth char) that decodes as cp932
with at most a few ASCII digits/codes mixed in, ended by NUL. For each string start, counts aligned words
0x08000000|start anywhere in the ROM and prints the pointer locations. Summary on stdout; detail in OUT.tsv:
start, end, n_ptrs, first_ptr_locs, text.
"""
import struct
import sys
from collections import defaultdict


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def scan(d):
    i, n = 0, len(d)
    out = []
    while i < n - 1:
        if not is_lead(d[i]):
            i += 1
            continue
        j, jp = i, 0
        ok = True
        while j < n and d[j] != 0:
            b = d[j]
            if is_lead(b):
                try:
                    bytes(d[j:j + 2]).decode("cp932")
                except UnicodeDecodeError:
                    ok = False
                    break
                jp += 1
                j += 2
            elif 0x20 <= b < 0x7F or b in (0x0A, 0x0D):
                j += 1
            else:
                ok = False
                break
        if ok and j < n and d[j] == 0 and jp >= 1:
            # back up: string may start with ascii codes before the first lead byte
            s = i
            while s > 0 and 0x20 <= d[s - 1] < 0x7F:
                s -= 1
            out.append((s, j))
            i = j + 1
        else:
            i = max(j, i + 1) if not ok else j + 1
    return out


def main():
    d = open(sys.argv[1], "rb").read()
    strs = scan(d)
    starts = {s for s, _ in strs}
    ptrs = defaultdict(list)
    for k in range(0, len(d) - 3, 4):
        v = struct.unpack_from("<I", d, k)[0]
        if 0x08000000 <= v < 0x08000000 + len(d) and (v - 0x08000000) in starts:
            ptrs[v - 0x08000000].append(k)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        for s, e in strs:
            p = ptrs.get(s, [])
            t = d[s:e].decode("cp932", "replace").replace("\t", " ").replace("\n", "\\n")
            f.write(f"{s:06x}\t{e:06x}\t{len(p)}\t{','.join(f'{x:06x}' for x in p[:4])}\t{t}\n")
    withp = [x for x in strs if ptrs.get(x[0])]
    print(f"{len(strs)} strings, {sum(e - s for s, e in strs)} bytes; with pointers {len(withp)}, "
          f"{sum(e - s for s, e in withp)} bytes")


if __name__ == "__main__":
    main()
