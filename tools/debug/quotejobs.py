"""Text coverage for battle quote tables: run quotecycle.lua in parallel battles, one slice of quotes per job.

    python -X utf8 tools/debug/quotejobs.py [--jobs 16] [--total 1580] [--per-table 158] [--only 3,7]

Each job warps to a battle (scene `qc_battle`: the /035 battle of battle_forest), keeps both HPs full (KEEP) so the
battle never ends, mashes A, and forces quotes START..START+COUNT-1 through the quote picker (tools/debug/quotecycle.lua),
with the skill's textcover.lua probe logging every text read. Logs go to work/qa/cover/quotes/jNN/log.txt, where
`tools/debug/cover.py report` counts them. A job that never logs QC_END ran out of frames: re-run it with --only.
"""
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "debug"))
from skill import SKILL  # noqa: E402
import cover  # noqa: E402

OUT = ROOT / "work" / "qa" / "cover" / "quotes"
KEEP = "0x02019938:290,0x02019944:208"  # player / enemy shikigami HP (docs/re/debug.md)
SCENE = "qc_battle raw /0350110000800060000 until_op=035 hold=900000\n"
FRAMES_PER_QUOTE = 1600


LITS = [0x104EDC, 0x104EE4, 0x104EEC, 0x104EF4, 0x104EFC, 0x104F04, 0x104F0C, 0x104F14, 0x104F1C, 0x104F34]


def missing(per_table):
    """table*1000+entry of every quote-table slot whose string the last report never saw."""
    import struct
    rom = cover.ROOT.joinpath("rom", "Onmyou Taisenki Zeroshiki (Japan).gba").read_bytes()
    unseen = {int(l.split()[2], 16) for l in (cover.OUT / "report.txt").read_text(encoding="utf-8").splitlines()
              if l.startswith("NEVER SHOWN")}
    out = []
    for t, lit in enumerate(LITS):
        base = struct.unpack_from("<I", rom, lit)[0] - 0x08000000
        for i in range(per_table):
            p = struct.unpack_from("<I", rom, base + 4 * i)[0] - 0x08000000
            if p in unseen:
                unseen.discard(p)
                out.append(t * 1000 + i)
    return out


def run(j, start, count, lst=None):
    d = OUT / (f"m{j:02d}" if lst else f"j{j:02d}")
    d.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts" / "emu.py"), str(cover.ROM), "--out", str(d),
           "--script", str(ROOT / "tools" / "debug" / "warp.lua"), "--var", "SCENE='qc_battle'",
           "--var", f"SCENES_FILE='{(OUT / 'scenes.txt').as_posix()}'",
           "--script", str(ROOT / "tools" / "debug" / "quotecycle.lua"),
           "--script", str(Path(SKILL) / "scripts" / "lua" / "probes" / "textcover.lua"),
           "--var", f"RANGES='{cover.ranges()}'", "--var", f"START={start}", "--var", f"COUNT={count}",
           "--var", f"PER_TABLE={A.per_table}", "--var", f"KEEP='{KEEP}'",
           "--frames", str(4000 + count * FRAMES_PER_QUOTE), "--timeout", "3000", "--mash", "40"]
    if lst:
        cmd += ["--var", f"LIST='{','.join(map(str, lst))}'"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = (d / "log.txt").read_text(encoding="utf-8", errors="replace") if (d / "log.txt").exists() else ""
    n = log.count("\nQC ") + log.startswith("QC ")
    ok = "QC_END" in log
    return j, ok, n, r.returncode


def main():
    global A
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--total", type=int, default=1580)
    ap.add_argument("--per-table", type=int, default=158)
    ap.add_argument("--only", help="comma-separated job numbers to (re)run")
    ap.add_argument("--missing", action="store_true",
                    help="only the quotes work/qa/cover/report.txt lists as unseen, each forced twice (jobs mNN)")
    A = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scenes.txt").write_text(SCENE, encoding="utf-8")
    size = -(-A.total // A.jobs)
    work = []
    for j in range(A.jobs):
        first = j * size
        if first >= A.total:
            break
        count = min(size, A.total - first)
        start = (first // A.per_table) * 1000 + first % A.per_table
        work.append((j, start, count))
    if A.missing:
        todo = missing(A.per_table)
        print(f"{len(todo)} unseen quotes")
        n = -(-len(todo) // A.jobs)
        work = [(j, 0, 2 * len(todo[j * n:(j + 1) * n]), todo[j * n:(j + 1) * n])
                for j in range(A.jobs) if todo[j * n:(j + 1) * n]]
    if A.only:
        keep = {int(x) for x in A.only.split(",")}
        work = [w for w in work if w[0] in keep]
    bad = 0
    with ThreadPoolExecutor(len(work)) as ex:
        for j, ok, n, rc in ex.map(lambda w: run(*w), work):
            print(f"j{j:02d} {'ok ' if ok else 'BAD'} quotes={n} exit={rc}")
            bad += not ok
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
