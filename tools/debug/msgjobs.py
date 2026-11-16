"""Text coverage for battle messages: run msgcycle.lua in parallel battles, one slice of unseen messages per job.

    python -X utf8 tools/debug/cover.py report      # first: work/qa/cover/report.txt
    python -X utf8 tools/debug/msgjobs.py [--jobs 8] [--files str_battle_msgs,str_tutorial_help] [--ids 410EC4,..]

Takes every id of the given files that the last report lists as never shown (or the --ids given), looks up its
built address in build/strings.tsv, and forces each through the battle message drawer twice
(tools/debug/msgcycle.lua) in the battle_forest /035 battle with both HPs held. Logs:
work/qa/cover/msgs/jNN/log.txt (counted by `cover.py report`). A job without MC_END ran out of frames.
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "debug"))
from skill import SKILL  # noqa: E402
import cover  # noqa: E402
import labeljobs  # noqa: E402
import quotejobs  # noqa: E402

OUT = ROOT / "work" / "qa" / "cover" / "msgs"
FRAMES_PER_MSG = 900


def targets(files, ids):
    built = dict(l.split("\t") for l in cover.STRINGS.read_text(encoding="utf-8").splitlines() if l)
    if ids:
        want = [int(i, 16) for i in ids.split(",")]
    else:
        miss = labeljobs.unseen()
        want = []
        for f in files.split(","):
            for e in json.loads((ROOT / "script" / f"{f}.json").read_text(encoding="utf-8"))["entries"]:
                if int(e["id"], 16) in miss:
                    want.append(int(e["id"], 16))
    return [int(built[f"{i:06X}"], 16) for i in want]


def run(j, addrs, tag="j"):
    d = OUT / f"{tag}{j:02d}"
    d.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts" / "emu.py"), str(cover.ROM), "--out", str(d),
           "--script", str(ROOT / "tools" / "debug" / "warp.lua"), "--var", "SCENE='qc_battle'",
           "--var", f"SCENES_FILE='{(OUT / 'scenes.txt').as_posix()}'",
           "--script", str(ROOT / "tools" / "debug" / "msgcycle.lua"),
           "--script", str(Path(SKILL) / "scripts" / "lua" / "probes" / "textcover.lua"),
           "--var", f"RANGES='{cover.ranges()}'", "--var", f"KEEP='{quotejobs.KEEP}'",
           "--var", "ADDRS='" + ",".join(f"0x{a:08X}" for a in addrs) + "'",
           "--frames", str(4000 + 2 * len(addrs) * FRAMES_PER_MSG), "--timeout", "3000", "--mash", "40"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = (d / "log.txt").read_text(encoding="utf-8", errors="replace") if (d / "log.txt").exists() else ""
    return j, "MC_END" in log, sum(1 for l in log.splitlines() if l.startswith("MC ")), r.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--files", default="str_battle_msgs,str_tutorial_help")
    ap.add_argument("--ids")
    ap.add_argument("--tag", default="j", help="job dir prefix (a second run with another tag keeps the first's logs)")
    a = ap.parse_args()
    addrs = targets(a.files, a.ids)
    print(f"{len(addrs)} messages")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scenes.txt").write_text(quotejobs.SCENE, encoding="utf-8")
    size = -(-len(addrs) // a.jobs)
    slices = [addrs[k:k + size] for k in range(0, len(addrs), size)]
    with ThreadPoolExecutor(len(slices)) as ex:
        for j, ok, n, rc in ex.map(lambda p: run(*p, a.tag), enumerate(slices)):
            print(f"{a.tag}{j:02d}{'ok ' if ok else 'CUT'} forced {n} rc {rc}")


if __name__ == "__main__":
    main()
