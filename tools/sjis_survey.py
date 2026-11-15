"""sjis_survey.py ROM [min_chars]: list Shift-JIS text runs that read as text (kana-heavy), grouped by 64 KiB region.

Recon helper (read-only). Prints region histogram, then with --dump every run as `offset<TAB>text`.
"""
import sys
from collections import Counter


def runs(data, min_chars=2):
    i, n = 0, len(data)
    while i < n:
        j, chars = i, []
        while j < n:
            b = data[j]
            if 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEA:
                if j + 1 >= n:
                    break
                try:
                    c = bytes(data[j:j + 2]).decode("cp932")
                except UnicodeDecodeError:
                    break
                chars.append(c)
                j += 2
            elif 0x20 <= b < 0x7F and chars:
                chars.append(chr(b))
                j += 1
            else:
                break
        if len(chars) >= min_chars:
            s = "".join(chars)
            kana = sum(1 for c in s if "぀" <= c <= "ヿ" or c in "、。！？「」…ー")
            if kana * 3 >= len(s) or len(s) >= 6 and kana >= 2:
                yield i, j, s
            i = j
        else:
            i += 1


def main():
    data = open(sys.argv[1], "rb").read()
    mn = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 2
    hits = list(runs(data, mn))
    reg = Counter()
    for a, b, s in hits:
        reg[a >> 16] += b - a
    if "--dump" in sys.argv:
        for a, b, s in hits:
            print(f"{a:06x}\t{b - a}\t{s}")
    else:
        print(f"{len(hits)} runs, {sum(reg.values())} bytes")
        for r in sorted(reg):
            print(f"  {r << 16:06x}: {reg[r]} bytes")


if __name__ == "__main__":
    main()
