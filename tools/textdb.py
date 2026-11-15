"""textdb.py: the repo's text files (script/*.json) <-> the ROM's event scripts and string tables.

    python -X utf8 tools/textdb.py dump [--force]   # write script/*.json from the original ROM
    python -X utf8 tools/textdb.py stats            # entries / translated per file
    python -X utf8 tools/textdb.py coverage         # text-like runs that are neither dumped nor listed as data

Two kinds of file, one entry per translatable unit, `id` = its file offset in the ORIGINAL ROM (hex, stable):
  ev_<block>.json / tutorial.json  every text run of the event scripts (tools/evscript.py), grouped by the 16 KiB
      block of the script start. Extra fields: `script` (script offset), `op` (the opcode + args the run follows:
      `073 0001` dialogue, `036`/`098`/`124`... speaker or branch set-ups; the speaker is in the args, never in the
      text). Control codes stay inline as `{0000}` newline, `{0010}` page break, `{00C8}` player name ...
  str_<group>.json  every NUL-terminated string a pointer reaches (tools/strtab.py). Extra fields: `max` (bytes the
      string may take in place incl. NUL; longer ones move to free space and get repointed), `pad` (fixed-width
      lines: the JP pads each line with `　` to this many characters instead of a newline code; a guess from the
      text, check in-game), `ptrs` (pointer words when more than one).
Every entry: `jp` (decoded original, `[XXXX]` = a Shift-JIS pair that doesn't roundtrip), `en` ("" = keep JP),
optional `notes`. Gaiji: the font draws extra kanji at the Cyrillic codes 0x8440.. (GAIJI); `notes` spells them.

`dump` never clobbers English: it writes missing files only; with --force it rewrites the JP side and keeps every
existing entry's `en`/`notes`/`status` by id. build.py calls `overrides()`, which refuses JSON whose `jp` no longer
matches the ROM.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enfont  # noqa: E402
import evscript  # noqa: E402
import strtab  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba"
DIR = ROOT / "script"
KEEP = ("en", "notes", "status")  # translator-owned fields a re-dump keeps

# String groups: (first string offset, name). A string belongs to the last group starting at or before it.
GROUPS = [
    (0x120000, "debug_menu"),      # ●ＭＡＰ / シナリオ / パレット ...: a leftover graphics-viewer menu
    (0x126190, "battle_help"),     # battle command help (fixed width), name-entry kana row
    (0x127968, "save"),
    (0x12802C, "intro"),           # opening scroll
    (0x1283F8, "credits"),         # staff roll (D3: English)
    (0x128F64, "system"),          # system messages, status labels, items
    (0x12B024, "shikigami_names"),  # 5-cell names copied to RAM at boot (text.md "Shikigami name variables")
    (0x12B440, "shikigami_kinds"),
    (0x12B644, "skills"),
    (0x12BA4C, "weapons"),
    *[(a, f"quotes{n:02d}") for n, a in enumerate(
        [0x12BDC8, 0x12D284, 0x12ECD8, 0x1302B8, 0x131E48, 0x1337D4, 0x134D88, 0x13644C, 0x137898, 0x13926C], 1)],
    (0x13AC10, "abilities"),
    (0x13B854, "techniques_a"),
    (0x13BEA8, "techniques_b"),
    *[(a, f"tech_quotes{n}") for n, a in enumerate([0x4083A8, 0x408CC4, 0x409500, 0x409D70, 0x40A568], 1)],
    (0x40B6B4, "areas"),
    (0x40C2A0, "name_entry"),      # character grid rows: glyph sets, not sentences
    (0x40C698, "menus"),           # rules / link-cable menus
    (0x40C9BC, "battle_msgs"),
    (0x40EB5C, "battle_kanji"),    # one-kanji lookup keys for the super-move cut-in (0x08109614)
    (0x40F718, "menus2"),
    (0x410AE4, "tutorial_help"),
    (0x413BFC, "char_names"),
]

ABOUT = {
    "str_debug_menu": "Leftover graphics-viewer debug menu; not reached in normal play. Kept Japanese (D9).",
    "str_battle_help": "Battle command help rows; their only reader (0x0800F010) is dead code. Kept Japanese (D9).",
    "str_name_entry": "Name-entry screen. Grid rows are glyph sets (keep, the ABC tab gives English letters); "
                      "translate only the title 40C524, label 40C530, default name 40C51C (<= 4 letters), the "
                      "prompts and the link-cable messages.",
    "str_shikigami_names": "Shikigami names: the game copies 5 cells per name to RAM at boot (docs/re/text.md); "
                           "longer English names need that copy widened (phase 5).",
    "str_battle_kanji": "Lookup keys, not text: 0x08109614 matches each kanji of a techniques_b name against these "
                        "to pick the super-move cut-in graphic. Never translate.",
    "str_credits": "Staff roll; fixed-width rows centred with `　` (D3: translate).",
    "tutorial": "Battle-tutorial scripts (region 0x6918E8..0x693978).",
}

NOTES = {  # per-string notes the dump adds
    0x410E18: "digit glyph set (number drawing?): keep unless the font changes",
    0x12B644: "single `　`, shared by 73 pointers (empty skill slot)",
}

# Font cells at Cyrillic / NEC codes that hold kanji outside JIS level 1 (rendered from the font, 2026-11-16;
# `?` = unsure). 0x8457..0x8459 are half-cell pieces of two-character words.
GAIJI = {
    "А": "隕", "Б": "銛", "В": "曼", "Г": "祓", "Д": "撼", "Е": "鉈", "Ё": "鯔", "Ж": "咬", "З": "毬", "И": "棍",
    "Й": "穹?", "К": "棘", "Л": "龕", "М": "礫", "Н": "翔", "О": "跋", "П": "扈", "Р": "巫", "С": "澤", "Т": "條",
    "У": "晏", "Ф": "麒", "Х": "荼", "Ц": "ラ・", "Ч": "衛・(left)", "Ш": "・二(right)", "Ⅴ": "Ｖ",
}


# Shift-JIS-looking runs outside the text areas that are data (coverage check below), start -> what.
DATA_RUNS = {
    0x4E1DC9: "u16 LE table of Shift-JIS punctuation codes (。，．・：；？！), read as text one byte off",
    0x4E5C0F: "u16 LE table of Shift-JIS kana codes mixed with other words",
    0x4E5C4F: "same table as 0x4E5C0F",
    0x6EE2DB: "byte sequence in the music area",
}


def kana(s):
    return sum(1 for c in s if "ぁ" <= c <= "ヾ" or c in "、。！？「」…ー")


def uncovered(d):
    """Text-like Shift-JIS runs the dump doesn't hold and nothing lists as data: [(offset, text, where)].
    In the string areas: a scan candidate no pointer reaches with 2+ kana (the 148 unpointed candidates are 1-10
    byte fragments of code/graphics). Elsewhere: a run of 5+ Shift-JIS characters with 3+ kana and at most one
    ASCII byte, outside the script regions, string areas and DATA_RUNS."""
    import sjis_survey
    out = []
    st = strtab.Strings(d)
    for lo, hi in strtab.segments():
        for s, e in strtab.scan(d, lo, hi):
            if s not in st.strings and kana(d[s:e].decode("cp932", "replace")) >= 2:
                out.append((s, d[s:e].decode("cp932", "replace"), "string area, no pointer"))
    areas = list(strtab.AREAS) + list(evscript.REGIONS.values())
    for a, b, s in sjis_survey.runs(d, 3):
        if any(lo <= a < hi for lo, hi in areas) or a in DATA_RUNS:
            continue
        if sum(1 for c in s if ord(c) > 0x7F) >= 5 and kana(s) >= 3 and sum(1 for c in s if ord(c) < 0x80) <= 1:
            out.append((a, s, "outside the text areas"))
    return out


def decode_str(raw):
    """String-table bytes -> text, escaping pairs that don't roundtrip as [XXXX] (evscript's convention)."""
    out, p = [], 0
    while p < len(raw):
        b = raw[p]
        if evscript.is_lead(b):
            pair = raw[p:p + 2]
            try:
                ch = pair.decode("cp932")
                if ch.encode("cp932") != pair or ch in "{}[]":
                    raise UnicodeError
            except UnicodeError:
                ch = f"[{pair.hex().upper()}]"
            out.append(ch)
            p += 2
        else:
            ch = chr(b)
            if ch in "{}[]":
                raise ValueError(f"ASCII {ch!r} in a string table entry")
            out.append(ch)
            p += 1
    return "".join(out)


def encode_str(s):
    return evscript.encode_text(s)


def group_of(off):
    name = GROUPS[0][1]
    for a, n in GROUPS:
        if off >= a:
            name = n
    return name


def ev_file(script_off):
    lo, hi = evscript.REGIONS["tutorial"]
    if lo <= script_off < hi:
        return "tutorial"
    return f"ev_{script_off & ~0x3FFF:06X}"


def runs(sc):
    """Yield (script offset, token index, run offset, preceding op token, text) for every text run."""
    for off, toks in sorted(sc.scripts.items()):
        pos = off
        for i, t in enumerate(toks):
            if t[0] == "text":
                yield off, i, pos, toks[i - 1], t[1]
            pos += len(evscript.encode([t]))


def pad_width(jp):
    """Width of fixed-width lines if every inner run of `　` ends on a multiple of one width (and the first is 2+)."""
    ends = [(m.end(), len(m.group())) for m in re.finditer("　+", jp) if m.end() < len(jp)]
    if not ends or ends[0][1] < 2:
        return None
    w = ends[0][0]
    return w if all(e % w == 0 for e, _ in ends) else None


def gaiji_note(jp):
    hits = [f"{c}={GAIJI[c]}" for c in dict.fromkeys(jp) if c in GAIJI]
    return "gaiji " + " ".join(hits) if hits else ""


def dump_all(d):
    """{file name: [entries]} straight from the ROM, no translations."""
    files = {}
    for script, _, pos, op, text in runs(evscript.Scripts(d)):
        e = {"id": f"{pos:06X}", "script": f"{script:06X}", "op": f"{op[1]} {op[2]}".rstrip(), "jp": text, "en": ""}
        if gaiji_note(text):
            e["notes"] = gaiji_note(text)
        files.setdefault(ev_file(script), []).append(e)
    st = strtab.Strings(d)
    for off, raw in sorted(st.strings.items()):
        jp = decode_str(raw)
        e = {"id": f"{off:06X}", "jp": jp, "en": "", "max": st.room[off]}
        if pad_width(jp):
            e["pad"] = pad_width(jp)
        if len(st.refs[off]) > 1:
            e["ptrs"] = len(st.refs[off])
        note = "; ".join(x for x in (NOTES.get(off, ""), gaiji_note(jp)) if x)
        if note:
            e["notes"] = note
        files.setdefault(f"str_{group_of(off)}", []).append(e)
    return files


def load():
    """{file name: [entries]} from script/."""
    return {p.stem: json.loads(p.read_text(encoding="utf-8"))["entries"] for p in sorted(DIR.glob("*.json"))}


def write(name, entries):
    DIR.mkdir(exist_ok=True)
    body = {"file": name, **({"about": ABOUT[name]} if name in ABOUT else {}), "entries": entries}
    (DIR / f"{name}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def dump(d, force=False):
    fresh = dump_all(d)
    old = {e["id"]: e for es in load().values() for e in es} if DIR.exists() else {}
    wrote = 0
    for name, entries in fresh.items():
        if (DIR / f"{name}.json").exists() and not force:
            continue
        for e in entries:
            for k in KEEP:
                if old.get(e["id"], {}).get(k):
                    e[k] = old[e["id"]][k]
        write(name, entries)
        wrote += 1
    return wrote, len(fresh)


def overrides(d, files=None):
    """(scripts, strings) build overrides from entries with a non-empty `en`: {script offset: tokens},
    {string offset: bytes without NUL}. Raises if an entry's id or `jp` doesn't match the ROM."""
    files = load() if files is None else files
    sc = evscript.Scripts(d)
    where = {f"{pos:06X}": (script, i, text) for script, i, pos, _, text in runs(sc)}
    st = strtab.Strings(d)
    scripts, strings = {}, {}
    for name, entries in files.items():
        for e in entries:
            if name.startswith("str_"):
                off = int(e["id"], 16)
                if off not in st.strings or decode_str(st.strings[off]) != e["jp"]:
                    raise ValueError(f"{name} {e['id']}: jp doesn't match the ROM (re-dump?)")
                if e["en"]:
                    strings[off] = encode_str(enfont.encode_en(e["en"], string_table=True))
            else:
                if e["id"] not in where or where[e["id"]][2] != e["jp"]:
                    raise ValueError(f"{name} {e['id']}: jp doesn't match the ROM (re-dump?)")
                if e["en"]:
                    script, i, _ = where[e["id"]]
                    toks = scripts.setdefault(script, list(sc.scripts[script]))
                    toks[i] = ("text", enfont.encode_en(e["en"]))
    return scripts, strings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["dump", "stats", "coverage"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "dump":
        wrote, total = dump(ROM.read_bytes(), a.force)
        print(f"wrote {wrote} of {total} files in {DIR.relative_to(ROOT)}/")
    elif a.cmd == "coverage":
        bad = uncovered(ROM.read_bytes())
        for off, s, where in bad:
            print(f"{off:06X} {where}: {s[:40]}")
        print(f"{len(bad)} uncovered text-like runs")
        sys.exit(1 if bad else 0)
    else:
        files = load()
        n = sum(map(len, files.values()))
        done = sum(1 for es in files.values() for e in es if e["en"])
        chars = sum(len(re.sub(r"\{....\}", "", e["jp"])) for es in files.values() for e in es)
        print(f"{len(files)} files, {n} entries, ~{chars} JP chars, {done} translated")


if __name__ == "__main__":
    main()
