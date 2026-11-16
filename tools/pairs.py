"""Reviewer pairs files: every entry of a translation batch as `>> id | speaker | file | JP` / `EN` (current English
from script/, not the batch output, so fits and fixes after the merge are what gets reviewed).

    python -X utf8 tools/pairs.py [bNNN ...] [--out work/review]   one bNNN.pairs.txt per batch (default: all)
    python -X utf8 tools/pairs.py --chapters [--out work/qa/story/chapters]   story-pass files (CHAPTERS below)

Entries keep batch order, which is script order, so each line has its neighbours as context. Gaiji readings and
other notes ride along as `   # note`. The speaker column names the plate the op sets up: `036 00NN0001` = the
speaker plate's name table 0x0841392C[NN] (str_char_names; NN decimal, 0 = the player), `098 00NN000x` = the
shikigami name table 0x0812AEE0[NN] (Kogenta = 15); `073`/`124` = no plate (NPC or narration).
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402
import build  # noqa: E402

CHAR_NAMES, SHIKI_NAMES = 0x41392C, 0x12AEE0  # pointer tables (file offsets), 4 bytes per index

# Story-pass chapters in story order (docs/synopsis.md "Plot so far"): name -> script files. The contract scenes
# (ev_41C000-ev_430000) are side scenes, one per shikigami, so they get chapters of their own after the plot.
CHAPTERS = [
    ("ch01_prologue", ["ev_434000", "tutorial"]),
    ("ch02_school_letter", ["ev_438000"]),
    ("ch03_kidnapping_dam", ["ev_43C000", "ev_440000"]),
    ("ch04_chiryu_four_kings", ["ev_444000", "ev_448000"]),
    ("ch05_past_gosho", ["ev_44C000", "ev_450000"]),
    ("ch06_taihaku_fukumaden", ["ev_454000", "ev_458000"]),
    ("ch07_villages_finale", ["ev_45C000", "ev_460000"]),
    ("ch08_postgame_town", ["ev_464000", "ev_468000"]),
    ("ch09_contracts_a", ["ev_41C000", "ev_420000", "ev_424000"]),
    ("ch10_contracts_b", ["ev_428000", "ev_42C000"]),
    ("ch11_contracts_c", ["ev_430000"]),
]


def _name_table(rom, table, idx, count):
    out = {}
    for i in range(count):
        a = struct.unpack_from("<I", rom, table + 4 * i)[0]
        if not 0x08000000 <= a < 0x08800000:
            break
        e = idx.get(f"{a & 0xFFFFFF:06X}")
        if e and e.get("en"):
            out[i] = e["en"]
    return out


def speakers(idx):
    """op -> speaker label function, from the original ROM's two name tables."""
    rom = build.ROM.read_bytes()
    chars = _name_table(rom, CHAR_NAMES, idx, 0x80)
    shiki = _name_table(rom, SHIKI_NAMES, idx, 0x60)

    def label(op):
        parts = op.split()
        if len(parts) == 2 and parts[0] in ("036", "098") and len(parts[1]) == 8 and parts[1].isdigit():
            n = int(parts[1][:4])
            if parts[0] == "036":
                # 0, 11 and 19 point at the default player name リク: the plate shows the player's own name
                return "Player" if n in (0, 11, 19) else chars.get(n, f"char {n}")
            return shiki.get(n, f"shikigami {n}")
        return "(no plate)"
    return label


def pairs(batch, idx):
    lines = []
    for row in batches.read_tsv(batches.TL / f"{batch}.tsv"):
        eid, speaker, form = row[0], row[1], row[2]
        e = idx.get(eid)
        if e is None:
            lines.append(f">> {eid} | MISSING FROM script/")
            continue
        lines.append(f">> {eid} | {speaker or '-'} | {form} | {e.get('jp', '')}")
        if e.get("notes"):
            lines.append(f"   # {e['notes']}")
        lines.append(f"   {e.get('en', '') or '(empty)'}")
    return "\n".join(lines) + "\n"


def chapter(files, idx, label):
    lines = []
    for name in files:
        doc = json.loads((ROOT / "script" / f"{name}.json").read_text(encoding="utf-8"))
        lines.append(f"## {name}")
        for e in doc["entries"]:
            if not e.get("en"):
                continue
            lines.append(f">> {e['id']} | {label(e.get('op', ''))} | {e['jp']}")
            if e.get("notes"):
                lines.append(f"   # {e['notes']}")
            lines.append(f"   {e['en']}")
    return "\n".join(lines) + "\n"


def main(argv):
    chapters = "--chapters" in argv
    argv = [a for a in argv if a != "--chapters"]
    out = ROOT / ("work/qa/story/chapters" if chapters else "work/review")
    if "--out" in argv:
        i = argv.index("--out")
        out = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    out.mkdir(parents=True, exist_ok=True)
    idx = batches.index()
    if chapters:
        label = speakers(idx)
        for name, files in CHAPTERS:
            (out / f"{name}.txt").write_text(chapter(files, idx, label), encoding="utf-8", newline="\n")
        print(f"{len(CHAPTERS)} chapter files in {out}")
        return
    names = argv or [p.stem for p in batches.existing()]
    for name in names:
        (out / f"{name}.pairs.txt").write_text(pairs(name, idx), encoding="utf-8")
    print(f"{len(names)} pairs files in {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
