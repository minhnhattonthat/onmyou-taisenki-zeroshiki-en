"""Who launches each event script: /123 jumps (kind 0 = if flag, kind 4 = always) from other scripts, traced back
to a map script (id 8000 + map, or 7800 + map for maps 500+), plus the story flags each script sets with /029.

    python -X utf8 tools/script_refs.py [IDS..] [--rom ROM]

Prints, per target id: the map(s) whose map script reaches it, the referring chain, and the flags it sets.
Recon helper for tools/debug/scenes.txt (docs/re/debug.md).
"""
import argparse
import re
from collections import defaultdict
from pathlib import Path

from script_index import ROM, scripts

OP123 = re.compile(rb"/123(\d{4})(\d{4})(\d{4})(\d{4})(\d{4})")
OP029 = re.compile(rb"/029(\d{4})(\d{4})(\d{4})")


def body(d, off):
    return d[off:d.find(b"/999", off)]


def map_of(sid):
    if 8000 <= sid < 8300:
        return sid - 8000
    if sid >= 8300:
        return sid - 7800
    return None


def build(d):
    refs = defaultdict(set)   # target -> {(source, kind, flag, val)}
    sets = {}
    offs = {}
    for sid, off, _, _ in scripts(d):
        offs[sid] = off
        b = body(d, off)
        for m in OP123.finditer(b):
            kind, var, val, tgt = (int(x) for x in m.groups()[:4])
            if tgt != 9999 and tgt != sid:
                refs[tgt].add((sid, kind, var, val))
        sets[sid] = [(int(v), int(x)) for k, v, x in OP029.findall(b) if int(k) == 0]
    return refs, sets, offs


def maps_for(refs, sid, seen=None, depth=0):
    seen = seen if seen is not None else set()
    if sid in seen or depth > 8:
        return []
    seen.add(sid)
    m = map_of(sid)
    if m is not None:
        return [(m, [sid])]
    out = []
    for src, kind, var, val in sorted(refs.get(sid, ())):
        for mp, chain in maps_for(refs, src, seen, depth + 1):
            out.append((mp, chain + [sid]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", type=int)
    ap.add_argument("--rom", default=str(ROM))
    a = ap.parse_args()
    d = Path(a.rom).read_bytes()
    refs, sets, offs = build(d)
    ids = a.ids or sorted(s for s in offs if s < 8000)
    for sid in ids:
        ms = maps_for(refs, sid)
        conds = sorted({(s, k, v, x) for s, k, v, x in refs.get(sid, ())})
        print(f"{sid}: maps={sorted({m for m, _ in ms})} via={[c for c in conds][:6]} sets={sets.get(sid, [])[:12]}")


if __name__ == "__main__":
    main()
