"""Marker text (phase 5): every entry's `en` replaced by `[id] filler`, so a tour shows which entry each box draws,
how wide each box is, and which Japanese is not in script/ at all.

    python -X utf8 build.py --marker [--out build/marker.gba]

Rules (build-time only, script/*.json is not touched):
  * every budget comes from tbl/windows.json (tools/windows.py); `python -X utf8 tools/lint.py --marker` proves
    every marker fits it.
  * script runs: each line ({0000}/{0010} split) filled to the dialogue px (the last line of a page to last_px:
    the page-wait orb); the first line starts with `[id] `; variable codes ({00C8}...) kept at the end of their line.
  * strings: filled to their variant's px in its font (small-font labels/tags in ensmall px), one line per JP line
    for pad strings (capped at the variant's lines), all lines for multi-line variants; `[id]` + filler when that
    fits, else the longest tail of the id that fits.
  * SKIP: glyph grids and data-like strings stay Japanese.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enfont  # noqa: E402
import windows  # noqa: E402

FILLER = "The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs! "
SKIP_FILES = {"str_name_entry"}
SKIP_IDS = {"410E18", "12B644"}  # digit glyph set; shared single-space empty slot
CODE = re.compile(r"\{[0-9A-Fa-f]{4}\}")


def fill(prefix, px, font="big", chars=None):
    s, i = prefix, 0
    while (windows.text_width(s + FILLER[i % len(FILLER)], font) <= px
           and (chars is None or len(s) < chars)):
        s += FILLER[i % len(FILLER)]
        i += 1
    return s.rstrip()


def script_marker(eid, jp):
    out, first = [], True
    parts = re.split(r"(\{0000\}|\{0010\})", jp)
    dlg = windows.data()["variants"]["dialogue"]
    for i, part in enumerate(parts):
        if part in ("{0000}", "{0010}"):
            out.append(part)
            continue
        if not part:
            continue
        codes = CODE.findall(part)
        last = i + 1 >= len(parts) or parts[i + 1] == "{0010}"  # last line of a page: the wait orb takes x 226..
        text = fill(f"[{eid}] " if first else "", dlg["last_px" if last else "px"] - 64 * len(codes))
        first = False
        out.append(text + "".join(codes))
    return "".join(out)


def string_marker(eid, e, file):
    """Filled to the entry's budget from tbl/windows.json (font, px, lines, chars)."""
    b = windows.budget(file, e)
    px, lines, font, _ = b if b else (16 * len(e["jp"]), 1, "big", "")
    chars = windows.variant(file, e)[1].get("chars") if b else None
    w = lambda s: windows.text_width(s, font)  # noqa: E731
    if e.get("pad") or lines > 1:
        n = min(lines, windows.jp_lines(e)) if e.get("pad") else lines
        rows = windows.variant(file, e)[1].get("row_px") if b else None
        return "\n".join(fill(f"[{eid}] " if i == 0 else "", rows[min(i, len(rows) - 1)] if rows else px, font, chars)
                         for i in range(n))
    if w(f"[{eid}]") <= px:
        return fill(f"[{eid}]", px, font, chars)
    for k in range(len(eid), 0, -1):
        if w(eid[-k:]) <= px or k == 1:
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
                e["en"] = string_marker(e["id"], e, name)
            else:
                e["en"] = script_marker(e["id"], e["jp"])
            new.append(e)
        out[name] = new
    return out
