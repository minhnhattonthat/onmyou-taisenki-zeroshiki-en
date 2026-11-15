"""Window data (the width gate): which box variant draws each entry and how much fits there.

    python -X utf8 tools/windows.py map work/qa/dc [build/marker.gba]   # who draws what, from a drawcalls.lua tour
    python -X utf8 tools/windows.py show                                # every variant with its budget and files

Data: tbl/windows.json
  variants: name -> {font: big|small, px: line budget, lines: max lines (0 = per entry from the JP), status:
            measured|guess, shot: proof, renderer, note}; "px": "jp" = the JP's own cell width (16 px a JP char in
            the big font, 8 in the small font) because the field is boxed by the next thing drawn.
  files:    file name (or prefix ending in *) -> variant
  ids:      entry id -> variant (overrides files)
API: variant(file, entry) -> (name, dict); budget(file, entry) -> (px per line, max lines, font, status).
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import enfont  # noqa: E402
import ensmall  # noqa: E402

DATA = ROOT / "tbl" / "windows.json"
_data = None


def data():
    global _data
    if _data is None:
        _data = json.loads(DATA.read_text(encoding="utf-8"))
    return _data


def variant(file, entry):
    d = data()
    name = d["ids"].get(entry["id"])
    if name is None:
        name = d["files"].get(file)
    if name is None:
        for k, v in d["files"].items():
            if k.endswith("*") and file.startswith(k[:-1]):
                name = v
                break
    if name is None:
        return None, None
    return name, d["variants"][name]


def jp_lines(entry):
    """The JP's own lines: pad strings wrap every `pad` chars, others are one line."""
    jp = entry["jp"]
    if entry.get("pad"):
        return max(1, -(-len(jp) // entry["pad"]))
    return 1


def budget(file, entry):
    """(px per line, max lines, font, status) or None when no variant covers the entry."""
    name, v = variant(file, entry)
    if v is None:
        return None
    px = v["px"]
    if px == "jp":
        per = 16 if v["font"] == "big" else 8
        px = per * (entry["pad"] if entry.get("pad") else len(entry["jp"]))
    lines = v.get("lines") or jp_lines(entry)
    return px, lines, v["font"], v["status"]


def text_width(s, font):
    return (enfont if font == "big" else ensmall).text_width(s)


# --- map: drawcalls.lua tour -> who draws what ---------------------------------------------------------------
ROUTINES = {
    "080029F0": "window", "080144F4": "padded", "080235D4": "intro_strip", "08023E3C": "credits_strip",
    "0803A168": "mapline", "08110BAC": "battle_line", "08110C88": "battle_2row", "08110AE8": "small_label",
    "08014098": "obj_cells", "08111B50": "small_tag",
}
DRAW = re.compile(r"DRAW f\d+ fn=(\w+) lr=(\w+) str=(\w+) a=(\w+) hex=(\w*)")


def placed(writes):
    """ROM offset -> entry id, from a build's .writes log (who = 'string <id>')."""
    out = {}
    for line in writes.read_text(encoding="utf-8").splitlines():
        off, _old, _new, *who = line.split(" ")
        if len(who) == 2 and who[0] == "string":
            out.setdefault(int(off, 16), who[1])
    return out


def decode(hx):
    rev = {v: k for k, v in enfont.CODES.items()}
    b = bytes.fromhex(hx)
    s = []
    for i in range(0, len(b) - 1, 2):
        c = b[i] << 8 | b[i + 1]
        if c == 0 or b[i] == 0:
            break
        s.append(rev.get(c, "?"))
    return "".join(s)


def cmd_map(tour, rom):
    where = placed(Path(rom).with_suffix(".writes"))
    files = {}
    for f in (ROOT / "script").glob("*.json"):
        for e in json.loads(f.read_text(encoding="utf-8"))["entries"]:
            files[e["id"]] = f.stem
    seen = defaultdict(set)  # id -> {(routine, lr, arg)}
    scenes = defaultdict(set)
    unknown = defaultdict(set)
    for log in sorted(Path(tour).glob("*/log.txt")):
        for m in DRAW.finditer(log.read_text(encoding="utf-8", errors="replace")):
            fn, lr, p, a, hx = m.groups()
            p = int(p, 16)
            eid = where.get(p - 0x08000000) if p >= 0x08000000 else None
            text = decode(hx) if hx else ""
            if eid is None:
                mm = re.search(r"\[([0-9A-F]{6})\]", text)
                eid = mm.group(1) if mm and mm.group(1) in files else None
            key = (ROUTINES.get(fn, fn), lr, a)
            if eid:
                seen[eid].add(key)
                scenes[eid].add(log.parent.name)
            else:
                unknown[key].add(text[:24] or f"@{p:08X}")
    out = Path(tour) / "drawmap.tsv"
    rows = []
    for eid in sorted(seen, key=lambda i: (files.get(i, "?"), i)):
        for r, lr, a in sorted(seen[eid]):
            rows.append(f"{files.get(eid, '?')}\t{eid}\t{r}\t{lr}\t{a}\t{','.join(sorted(scenes[eid]))}")
    out.write_text("file\tid\troutine\tlr\targ\tscenes\n" + "\n".join(rows) + "\n", encoding="utf-8")
    per = defaultdict(lambda: defaultdict(int))
    for eid, keys in seen.items():
        for r, lr, a in keys:
            per[files.get(eid, "?")][(r, lr)] += 1
    for f in sorted(per):
        print(f, " ".join(f"{r}@{lr}:{n}" for (r, lr), n in sorted(per[f].items())))
    print(f"{len(seen)} entries mapped -> {out}; unmapped draws: {len(unknown)}")
    for (r, lr, a), texts in sorted(unknown.items()):
        print(f"  ? {r}@{lr} a={a}: {' | '.join(sorted(texts)[:4])}")


def fill_exact(px, font="big", head="", tail="]"):
    """A line exactly px wide (head + letters + tail), for width-gate stress lines (`build.py --qa ID=...`)."""
    mod = enfont if font == "big" else ensmall
    letters = [c for c in "HMWmnoeaxsrcvzI1il." if c in enfont.CODES]
    widths = {mod.width(c): c for c in reversed(letters)}
    need = px - mod.text_width(head + tail)
    best = {0: ""}  # reachable width -> shortest string
    for w in range(1, need + 1):
        cands = [best[w - k] + c for k, c in widths.items() if w - k in best]
        if cands:
            best[w] = min(cands, key=len)
    if need not in best:
        raise SystemExit(f"cannot fill {px} px exactly")
    body = "".join(sorted(best[need], key=lambda c: -mod.width(c)))
    return head + body + tail


def cmd_show():
    d = data()
    by = defaultdict(list)
    for k, v in d["files"].items():
        by[v].append(k)
    for k, v in d["ids"].items():
        by[v].append(k)
    for name, v in d["variants"].items():
        print(f"{name:16} {v['font']:5} px={v['px']!s:4} lines={v.get('lines') or 'jp'} {v['status']:8} "
              f"{', '.join(by[name])}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["map"]:
        cmd_map(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else str(ROOT / "build" / "marker.gba"))
    elif sys.argv[1:2] == ["fill"]:  # fill PX [big|small] [head]
        print(fill_exact(int(sys.argv[2]), *(sys.argv[3:5] or ["big"])))
    elif sys.argv[1:2] == ["show"]:
        cmd_show()
    else:
        sys.exit(__doc__)
