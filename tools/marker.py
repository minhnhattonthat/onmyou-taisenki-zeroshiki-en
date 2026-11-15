"""Marker text (phase 5): every entry's `en` replaced by `[id] filler`, so a tour shows which entry each box draws,
how wide each box is, and which Japanese is not in script/ at all.

    python -X utf8 build.py --marker [--out build/marker.gba]

Rules (build-time only, script/*.json is not touched):
  * script runs: each line ({0000}/{0010} split) filled with FILLER to LINE_PX px of the VWF font; the first line
    starts with `[id] `; variable codes ({00C8}...) kept at the end of their line.
  * pad strings (fixed-width lines, the string drawer 0x080144F4): one filled line per JP line, joined by the VWF
    newline code.
  * other strings: filled to the JP's cell width (16 px per JP character; every renderer is VWF): `[id]` + filler
    when that fits, else the longest tail of the id that fits.
  * SKIP: glyph grids and data-like strings stay Japanese.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enfont  # noqa: E402

LINE_PX = 224
FILLER = "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs! "
SKIP_FILES = {"str_name_entry"}
SKIP_IDS = {"410E18", "12B644"}  # digit glyph set; shared single-space empty slot
CODE = re.compile(r"\{[0-9A-Fa-f]{4}\}")


def fill(prefix, px):
    s, i = prefix, 0
    while enfont.text_width(s + FILLER[i % len(FILLER)]) <= px:
        s += FILLER[i % len(FILLER)]
        i += 1
    return s.rstrip()


def script_marker(eid, jp):
    out, first = [], True
    for part in re.split(r"(\{0000\}|\{0010\})", jp):
        if part in ("{0000}", "{0010}"):
            out.append(part)
            continue
        if not part:
            continue
        codes = CODE.findall(part)
        text = fill(f"[{eid}] " if first else "", LINE_PX - 64 * len(codes))
        first = False
        out.append(text + "".join(codes))
    return "".join(out)


def string_marker(eid, e):
    jp = e["jp"]
    if e.get("pad"):
        n = max(1, -(-len(jp) // e["pad"]))
        return "\n".join(fill(f"[{eid}] " if i == 0 else "", LINE_PX) for i in range(n))
    px = 16 * len(jp)  # every renderer is VWF now: the field is the JP's cells, 16 px each
    if enfont.text_width(f"[{eid}]") <= px:
        return fill(f"[{eid}]", px)
    for k in range(len(eid), 0, -1):
        if enfont.text_width(eid[-k:]) <= px or k == 1:
            return eid[-k:]


def markers(files):
    """Copy of textdb.load() output with every markable entry's `en` set."""
    out = {}
    for name, entries in files.items():
        new = []
        for e in entries:
            e = dict(e)
            if name in SKIP_FILES or e["id"] in SKIP_IDS or not e["jp"].strip("　"):
                e["en"] = ""
            elif name.startswith("str_"):
                e["en"] = string_marker(e["id"], e)
            else:
                e["en"] = script_marker(e["id"], e["jp"])
            new.append(e)
        out[name] = new
    return out
