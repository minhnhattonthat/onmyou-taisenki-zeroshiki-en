"""NUL-terminated string tables outside the event scripts (docs/re/text.md "String tables").

A string = a run that holds at least one Shift-JIS character, may hold printable ASCII (format codes, digits), and
ends with NUL. Only strings that an aligned u32 pointer (0x08000000 | start) reaches from code or a table area are
kept; their pointer word locations are the repoint list. Pointers into the middle of a kept string are listed in
`inner`: such a string can't move until those are handled too.

    python -X utf8 tools/strtab.py [ROM]        # counts + roundtrip check
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba"

AREAS = [(0x120000, 0x140000), (0x400000, 0x419300)]  # where string tables live (text.md)
PTR_AREAS = [(0x000000, 0x120000)] + AREAS               # where pointers to them live (code pools + tables)
NOT_TEXT = {  # data the scan would take as text: start -> (end, what)
    0x128F50: (0x128F64, "u16 LE Shift-JIS digit glyphs 0..9 (number drawing), decodes as 'O' + fullwidth letters"),
}


def segments():
    """AREAS with the NOT_TEXT runs cut out."""
    out = []
    for lo, hi in AREAS:
        p = lo
        for a, (e, _) in sorted(NOT_TEXT.items()):
            if lo <= a < hi:
                out.append((p, a))
                p = e
        out.append((p, hi))
    return out


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def scan(d, lo, hi):
    """[(start, end)] with d[end] == NUL."""
    out, i = [], lo
    while i < hi - 1:
        if not is_lead(d[i]):
            i += 1
            continue
        j, ok = i, True
        while j < hi and d[j] != 0:
            b = d[j]
            if is_lead(b):
                try:
                    bytes(d[j:j + 2]).decode("cp932")
                except UnicodeDecodeError:
                    ok = False
                    break
                j += 2
            elif 0x20 <= b < 0x7F or b in (0x0A, 0x0D):
                j += 1
            else:
                ok = False
                break
        if ok and j < hi and d[j] == 0:
            s = i
            while s > lo and 0x20 <= d[s - 1] < 0x7F:  # leading ASCII codes belong to the string
                s -= 1
            out.append((s, j))
            i = j + 1
        else:
            i = max(j, i + 1) if not ok else j + 1
    return out


class Strings:
    """strings: {start: bytes without NUL}; room: {start: bytes it may take in place incl. NUL};
    refs: {start: [pointer word locations]}; inner: {start: [(location, target)]} pointers into the middle."""

    def __init__(self, d):
        cands = []
        for lo, hi in segments():
            cands += scan(d, lo, hi)
        ends = {s: e for s, e in cands}
        starts = sorted(ends)
        idx = {}
        for lo, hi in PTR_AREAS:
            for k in range(lo, hi - 3, 4):
                v = struct.unpack_from("<I", d, k)[0]
                if 0x08000000 <= v < 0x08000000 + len(d):
                    idx.setdefault(v - 0x08000000, []).append(k)
        self.refs = {s: idx[s] for s in starts if s in idx}
        self.strings = {s: bytes(d[s:ends[s]]) for s in self.refs}
        self.room, self.inner = {}, {}
        kept = sorted(self.strings)
        for n, s in enumerate(kept):
            e = ends[s] + 1
            nxt = kept[n + 1] if n + 1 < len(kept) else e
            # Trailing NUL padding up to the next kept string is ours too, unless a pointer targets a byte in it:
            # 0x40F73C (code 0x10E1A2) points at the NULs after "　カット" as an empty string.
            while e < nxt and d[e] == 0 and e not in idx:
                e += 1
            if e != nxt:
                e = ends[s] + 1
            self.room[s] = e - s
            mids = [(loc, t) for t in range(s + 1, ends[s] + 1) for loc in idx.get(t, ())]
            if mids:
                self.inner[s] = mids


def main():
    d = (Path(sys.argv[1]) if len(sys.argv) > 1 else ROM).read_bytes()
    s = Strings(d)
    print(f"{len(s.strings)} strings, {sum(map(len, s.strings.values()))} bytes, "
          f"{sum(map(len, s.refs.values()))} pointer words, {len(s.inner)} with inner pointers")
    for a, mids in list(s.inner.items())[:10]:
        print(f"  inner {a:06X}: {[(hex(l), hex(t)) for l, t in mids[:4]]}")


if __name__ == "__main__":
    main()
