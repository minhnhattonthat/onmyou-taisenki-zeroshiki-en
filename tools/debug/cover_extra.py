"""Re-run the one-off text-coverage runs (credits, key items, misc, seal, wheel help, View foe) on the current build.

    python -X utf8 tools/debug/cover_extra.py [--only credits,keyitems,misc,seal2,wheelhelp,viewfoe_0x4C,viewfoe_0x4B]
                                              [--states work/qa/cover/tour14/st] [--jobs 4]

Every run logs through the skill's textcover.lua probe under work/qa/cover/<name>/, where `cover.py report` counts
it. The battle-only runs start from savestates (`--states`, default work/states; any state made on the current
string layout works, since the probe only watches ROM reads). Recipes from the session-26 notes in docs/status.md.
"""
import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "debug"))
import cover  # noqa: E402

ROM = "build/onmyou_zeroshiki_en.gba"


def skill():
    return subprocess.run([sys.executable, "tools/skill.py"], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def expand(route):
    """'(6 a;60 -)x6;300 -' -> '6 a;60 -;6 a;60 -;...;300 -' (emu.py takes no repeat groups)."""
    while True:
        m = re.search(r"\(([^()]*)\)x(\d+)", route)
        if not m:
            return route
        route = route[:m.start()] + ";".join([m.group(1)] * int(m.group(2))) + route[m.end():]


RING = "(6 a;60 -)x6;300 -"
EMU_RUNS = {
    "seal2": ("tutorial_battle", "6 up;120 -;(6 a;90 -)x6;6 left;120 -;(6 a;90 -)x60", []),
    "wheelhelp": ("battle_forest", RING + ";(10 right;120 -)x5;(10 left;120 -)x2", []),
    "viewfoe_0x4C": ("battle_forest", RING + ";10 l;300 -;10 b;200 -",
                     ["--script", "tools/debug/foepoke.lua", "--var", "FOE=0x4C"]),
    "viewfoe_0x4B": ("battle_forest", RING + ";10 l;300 -;10 b;200 -",
                     ["--script", "tools/debug/foepoke.lua", "--var", "FOE=0x4B"]),
}
WARP_RUNS = {
    "credits": "credits_long top 63 mash=0 hold=30000 frames=40000\n",
    "keyitems": "tools/debug/cover_keyitems.txt",
    "misc": "tools/debug/cover_misc.txt",
}


def run(name, states, probe, rng):
    out = f"work/qa/cover/{name}"
    var = ["--var", f"RANGES='{rng}'"]
    if name in EMU_RUNS:
        state, route, extra = EMU_RUNS[name]
        cmd = [sys.executable, "-X", "utf8", f"{skill()}/scripts/emu.py", ROM, "--out", out,
               "--state-in", f"{states}/{state}.mss", "--script", probe, *var, *extra,
               "--route-str", expand(route)]
    else:
        scenes = WARP_RUNS[name]
        if "\n" in scenes:
            os.makedirs(out, exist_ok=True)
            path = f"{out}/scenes.txt"
            with open(os.path.join(ROOT, path), "w", encoding="utf8") as f:
                f.write(scenes)
            scenes = path
        cmd = [sys.executable, "-X", "utf8", "tools/debug/warp_all.py", ROM, "--scenes", scenes, "--out", out,
               "--states", f"{out}/states", "--probe", probe, *var, "--jobs", "4"]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf8", errors="replace")
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
    return name, r.returncode, tail[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default=",".join([*WARP_RUNS, *EMU_RUNS]))
    ap.add_argument("--states", default="work/states")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    probe = f"{skill()}/scripts/lua/probes/textcover.lua"
    rng = cover.ranges()
    names = a.only.split(",")
    bad = [n for n in names if n not in WARP_RUNS and n not in EMU_RUNS]
    if bad:
        sys.exit(f"unknown run(s): {bad}")
    fails = 0
    with ThreadPoolExecutor(a.jobs) as ex:
        for name, rc, last in ex.map(lambda n: run(n, a.states, probe, rng), names):
            print(f"{name}: exit {rc}  {last}")
            fails += rc != 0
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
