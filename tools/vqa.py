"""Visual QA with codex (read-only): one codex run per qa_gate chunk, English sheet + original sheet per id.

    python -X utf8 tools/vqa.py work/qa/chunks/chunk_000.txt [...] [--jp work/qa/tour_jp] [--jobs 3]
Writes work/qa/verdicts/<chunk dir>_<chunk>.tsv (id<TAB>ok|issue<TAB>note) for qa_gate.py check; the raw reply and log go
beside it. The brief is docs/visual-qa-brief.md. A chunk whose reply misses an id is reported, not written.
"""
import argparse
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def jp_sheet(en, tour_jp):
    p = Path(en)
    alt = Path(tour_jp) / p.parent.name / p.name
    return alt if alt.exists() else None


def run(chunk, tour_jp, out_dir):
    rows = [l.split("\t") for l in Path(chunk).read_text(encoding="utf-8").splitlines() if "\t" in l]
    args, lines = [], []
    n = 0
    for sid, path in rows:
        n += 1
        args += ["-i", str(path)]
        line = f"image {n}: id {sid} (English build)"
        jp = jp_sheet(path, tour_jp)
        if jp:
            n += 1
            args += ["-i", str(jp)]
            line += f"; image {n}: same id, original Japanese ROM"
        lines.append(line)
    brief = (ROOT / "docs" / "visual-qa-brief.md").read_text(encoding="utf-8")
    glossary = (ROOT / "glossary.md").read_text(encoding="utf-8")[:12000]
    prompt = (brief + "\n\n## This chunk\n" + "\n".join(lines)
              + "\n\nIds to judge (every one exactly once):\n" + "\n".join(r[0] for r in rows)
              + "\n\n## glossary.md (excerpt)\n" + glossary
              + "\n\nReply ONLY with the TSV verdict lines.")
    # chunk dir in the name: every todo run numbers its chunks from 000, so a bare stem would overwrite the
    # verdicts of an earlier round (chunks31/chunk_000 vs chunks33/chunk_000) and silently drop their ids.
    name = f"{Path(chunk).parent.name}_{Path(chunk).stem}"
    raw = out_dir / f"{name}.raw.txt"
    with open(out_dir / f"{name}.log", "w", encoding="utf-8") as log:
        subprocess.run(["codex", "exec", "-s", "read-only", "--skip-git-repo-check", "-o", str(raw), *args,
                        "--", prompt], stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
    got = {}
    if raw.exists():
        for l in raw.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*`?([^\t`]+)\t(ok|issue)\t(.*?)`?\s*$", l)
            if m:
                got[m.group(1).strip()] = (m.group(2), m.group(3).strip())
    missing = [r[0] for r in rows if r[0] not in got]
    if missing:
        return name, f"MISSING {missing}"
    (out_dir / f"{name}.tsv").write_text("".join(f"{r[0]}\t{got[r[0]][0]}\t{got[r[0]][1]}\n" for r in rows),
                                         encoding="utf-8")
    bad = [f"{r[0]}: {got[r[0]][1]}" for r in rows if got[r[0]][0] == "issue"]
    return name, f"{len(rows) - len(bad)} ok, {len(bad)} issue" + "".join("\n    " + b for b in bad)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chunks", nargs="+")
    ap.add_argument("--jp", default=str(ROOT / "work" / "qa" / "tour_jp"))
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "verdicts"))
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        for name, res in ex.map(lambda c: run(c, a.jp, out), a.chunks):
            print(f"{name}: {res}")


if __name__ == "__main__":
    main()
