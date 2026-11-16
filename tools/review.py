"""Independent reviewer pass with `codex exec` (read-only sandbox), one run per batch, brief docs/reviewer-brief.md.

    python -X utf8 tools/review.py [bNNN ...] [--jobs 6] [--redo]   reports -> work/review/bNNN.review.md
    python -X utf8 tools/review.py --summary                        Critical/Important counts + Assessment per batch

Run tools/pairs.py first. Existing reports are skipped unless --redo.
"""
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/review"

PROMPT = (
    "Follow docs/reviewer-brief.md exactly. Review the batch in work/review/{b}.pairs.txt (read all of it), using "
    "glossary.md, docs/style-reference.md, docs/synopsis.md and docs/decisions.md. Do not edit any file. Your final "
    "message is the report in the brief's format."
)


def run(batch):
    report = OUT / f"{batch}.review.md"
    cmd = ["codex", "exec", "-s", "read-only", "--skip-git-repo-check", "--ephemeral", "-C", str(ROOT),
           "-o", str(report), PROMPT.format(b=batch)]
    log = OUT / f"{batch}.codex.log"
    with log.open("w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
    ok = rc == 0 and report.exists() and report.stat().st_size > 0
    print(f"{batch} {'ok' if ok else f'FAILED rc={rc} (see {log.name})'}", flush=True)
    return ok


def section(text, name):
    m = re.search(rf"^###\s*{name}\s*$(.*?)(?=^###\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    return [ln for ln in m.group(1).splitlines() if ln.strip().startswith("- ") and "none" not in ln.lower()[:10]]


def summary():
    for rep in sorted(OUT.glob("b*.review.md")):
        t = rep.read_text(encoding="utf-8")
        a = re.search(r"###\s*Assessment\s*\n+(.*)", t)
        print(f"{rep.name[:4]} C={len(section(t, 'Critical'))} I={len(section(t, 'Important'))} "
              f"M={len(section(t, 'Minor'))} {a.group(1).strip()[:90] if a else '?'}")


def main(argv):
    if "--summary" in argv:
        return summary()
    jobs, redo = 6, "--redo" in argv
    if "--jobs" in argv:
        i = argv.index("--jobs")
        jobs = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    names = [a for a in argv if a.startswith("b")] or sorted(p.name[:4] for p in OUT.glob("b*.pairs.txt"))
    todo = [b for b in names if redo or not (OUT / f"{b}.review.md").exists()]
    with ThreadPoolExecutor(jobs) as pool:
        results = list(pool.map(run, todo))
    print(f"{sum(results)}/{len(todo)} reviews written")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) or 0)
