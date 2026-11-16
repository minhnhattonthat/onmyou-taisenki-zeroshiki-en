"""Story pass (phase 9, references/translation.md §Review): one independent `codex exec` reviewer (read-only sandbox)
per chapter, brief docs/story-reviewer-brief.md, then the verdict files the release gate checks.

    python -X utf8 tools/pairs.py --chapters                       work/qa/story/chapters/chNN_*.txt
    python -X utf8 <skill>/scripts/qa_gate.py init work/qa/story/manifest.tsv work/qa/story/chapters --glob "*.txt"
    python -X utf8 tools/story.py review [chNN ...] [--jobs 4] [--redo]   reports -> work/qa/story/reports/chNN.md
    python -X utf8 tools/story.py summary                          Critical/Important/Minor counts + Assessment
    python -X utf8 tools/story.py verdicts [chNN ...] [--fixed]    write work/qa/story/verdicts/<ch>.tsv from the
                                                                    reports' Assessment (--fixed: re-review after fixes)

Default chapters: those `qa_gate.py todo` would list (no current verdict). Existing reports are kept unless --redo.
"""
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "work/qa/story"
CHAPTERS, REPORTS, VERDICTS = STORY / "chapters", STORY / "reports", STORY / "verdicts"

PROMPT = (
    "Follow docs/story-reviewer-brief.md exactly. Read the whole chapter file work/qa/story/chapters/{c}.txt (in "
    "passes if needed), with docs/synopsis.md, docs/style-reference.md, glossary.md and docs/decisions.md. Do not edit "
    "any file. Your final message is the report in the brief's format."
)


def chapters(names):
    return names or sorted(p.stem for p in CHAPTERS.glob("*.txt"))


def run(c):
    REPORTS.mkdir(parents=True, exist_ok=True)
    report, log = REPORTS / f"{c}.md", REPORTS / f"{c}.codex.log"
    cmd = ["codex", "exec", "-s", "read-only", "--skip-git-repo-check", "--ephemeral", "-C", str(ROOT),
           "-o", str(report), PROMPT.format(c=c)]
    with log.open("w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
    ok = rc == 0 and report.exists() and report.stat().st_size > 0
    print(f"{c} {'ok' if ok else f'FAILED rc={rc} (see {log.name})'}", flush=True)
    return ok


def items(text, name):
    m = re.search(rf"^#+\s*{name}\b.*?$(.*?)(?=^#+\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    return [ln for ln in m.group(1).splitlines()
            if ln.strip().startswith("- ") and not re.match(r"-\s*none\b", ln.strip(), re.I)]


def assessment(text):
    m = re.search(r"^#+\s*Assessment\s*$(.*)", text, re.M | re.S)
    body = (m.group(1) if m else "").strip().strip("`*- ")
    word = re.match(r"`?(ok|issue)\b", body, re.I)
    return (word.group(1).lower() if word else "?"), " ".join(body.split())[:300]


def main(argv):
    if not argv or argv[0] not in ("review", "summary", "verdicts"):
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    jobs = int(args[args.index("--jobs") + 1]) if "--jobs" in args else 4
    names = [a for a in args if a.startswith("ch")]
    if cmd == "review":
        todo = [c for c in chapters(names) if "--redo" in args or not (REPORTS / f"{c}.md").exists()]
        with ThreadPoolExecutor(jobs) as ex:
            ok = list(ex.map(run, todo))
        return 0 if all(ok) else 1
    if cmd == "summary":
        for c in chapters(names):
            p = REPORTS / f"{c}.md"
            if not p.exists():
                print(f"{c}: no report")
                continue
            t = p.read_text(encoding="utf-8")
            word, note = assessment(t)
            print(f"{c}: C{len(items(t, 'Critical'))} I{len(items(t, 'Important'))} M{len(items(t, 'Minor'))} "
                  f"{word} - {note[:160]}")
        return 0
    VERDICTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d%H%M%S")
    for c in chapters(names):
        word, note = assessment((REPORTS / f"{c}.md").read_text(encoding="utf-8"))
        if word == "?":
            print(f"{c}: no Assessment word in the report; skipped")
            continue
        if "--fixed" in args and word == "ok":
            word = "fixed"
        (VERDICTS / f"{c}_{stamp}.tsv").write_text(f"{c}\t{word}\t{note}\n", encoding="utf-8", newline="\n")
        print(f"{c}\t{word}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
