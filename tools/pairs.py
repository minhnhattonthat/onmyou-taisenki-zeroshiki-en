"""Reviewer pairs files: every entry of a translation batch as `>> id | speaker | file | JP` / `EN` (current English
from script/, not the batch output, so fits and fixes after the merge are what gets reviewed).

    python -X utf8 tools/pairs.py [bNNN ...] [--out work/review]   one bNNN.pairs.txt per batch (default: all)

Entries keep batch order, which is script order, so each line has its neighbours as context. Gaiji readings and
other notes ride along as `   # note`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import batches  # noqa: E402


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


def main(argv):
    out = ROOT / "work/review"
    if "--out" in argv:
        i = argv.index("--out")
        out = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    names = argv or [p.stem for p in batches.existing()]
    out.mkdir(parents=True, exist_ok=True)
    idx = batches.index()
    for name in names:
        (out / f"{name}.pairs.txt").write_text(pairs(name, idx), encoding="utf-8")
    print(f"{len(names)} pairs files in {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
