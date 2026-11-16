"""Warp to every scene in tools/debug/scenes.txt from a cold boot; save a shot and a savestate per scene.

    python -X utf8 tools/debug/warp_all.py [ROM] [--only a,b] [--jobs 4] [--out work/qa/warp] [--states work/states]
                                           [--probe tools/debug/romreads.lua]

Each scene runs `emu.py ROM --script tools/debug/warp.lua --var SCENE='<name>'` (mash A unless the scene says
mash=0), and passes only if warp.lua logged SCENE_OK. Writes <out>/<scene>/scene.png, <states>/<scene>.mss, and
<out>/scenes.png (contact sheet of every scene.png). Exit 1 if any scene failed. This is the "regen all states"
command: re-run it after engine, font or graphics changes.
"""
import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from skill import SKILL  # noqa: E402

ROM = ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba"
PROBES = []  # extra --script probes (--probe)
SEQ = [0, 0]  # --seq N, --hold H
KINDS = {}    # scene name -> kind (script scenes hold 45 frames by default)
VARS = []     # extra --var for emu.py (--var), e.g. a probe's RANGES
DEFAULT_SCENES = ROOT / "tools" / "debug" / "scenes.txt"
SCENES = [DEFAULT_SCENES]  # --scenes


def kind_of(name):
    return KINDS.get(name, "")


def scenes(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, kind, *rest = line.split()
            opt = dict(t.split("=", 1) for t in rest if "=" in t)
            out.append((name, kind, opt))
    return out


def run(rom, name, opt, out, states):
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    for p in d.glob("*.png"):
        p.unlink()
    cmd = [sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts" / "emu.py"), str(rom), "--out", str(d),
           "--script", str(ROOT / "tools" / "debug" / "warp.lua"), "--var", f"SCENE='{name}'",
           "--frames", opt.get("frames", "20000"), "--timeout", "600",
           "--state-out", str((states / f"{name}.mss").resolve())]
    for p in PROBES:
        cmd += ["--script", str(Path(p).resolve())]
    for v in VARS:
        cmd += ["--var", v]
    if SCENES[0] != DEFAULT_SCENES:
        cmd += ["--var", f"SCENES_FILE='{SCENES[0].resolve().as_posix()}'"]
    mash = opt.get("mash", "40")
    if mash != "0":
        cmd += ["--mash", mash]
    if SEQ[0]:
        # longer hold so the sequence covers the scene; the scene's own hold wins when it is longer
        hold = max(int(opt.get("hold", "600" if kind_of(name) != "script" else "45")), SEQ[1])
        cmd += ["--var", f"SEQ={SEQ[0]}", "--var", f"HOLD={hold}",
                "--frames", str(int(opt.get("frames", "20000")) + hold)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = (d / "log.txt").read_text(encoding="utf-8", errors="replace") if (d / "log.txt").exists() else ""
    ok = r.returncode == 0 and "SCENE_OK" in log and (d / "scene.png").exists()
    if ok and SEQ[0]:
        seqs = sorted(str(p) for p in d.glob("seq_*.png"))
        if seqs:
            subprocess.run([sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts" / "sheet.py"), *seqs,
                            "--changed", "0.02", "--div", "1", "--cols", "3", "--out", str(d / "sheet.png")],
                           check=False, capture_output=True)
    line = next((l for l in log.splitlines() if l.startswith("SCENE_OK")), (r.stdout + r.stderr).strip()[-200:])
    return name, ok, line


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom", nargs="?", default=str(ROM))
    ap.add_argument("--only")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "work" / "qa" / "warp"))
    ap.add_argument("--states", default=str(ROOT / "work" / "states"))
    ap.add_argument("--probe", action="append", default=[], help="extra Lua probe run beside warp.lua (repeatable)")
    ap.add_argument("--seq", type=int, default=0, help="QA: a shot every N frames after the scene is reached, "
                    "and <out>/<scene>/sheet.png from them (--changed 0.02)")
    ap.add_argument("--hold", type=int, default=1500, help="with --seq: frames to keep running after the scene")
    ap.add_argument("--scenes", default=str(DEFAULT_SCENES), help="scene list (default tools/debug/scenes.txt; "
                    "tools/debug/cover.py writes one per event script for text coverage)")
    ap.add_argument("--var", action="append", default=[], help="extra emu.py --var (repeatable), e.g. a probe's")
    a = ap.parse_args()
    PROBES[:] = a.probe
    VARS[:] = a.var
    SEQ[:] = [a.seq, a.hold]
    SCENES[0] = Path(a.scenes)
    KINDS.update({n: k for n, k, _ in scenes(SCENES[0])})
    out, states = Path(a.out), Path(a.states)
    states.mkdir(parents=True, exist_ok=True)
    todo = scenes(SCENES[0])
    if a.only:
        keep = set(a.only.split(","))
        todo = [s for s in todo if s[0] in keep]
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda s: run(a.rom, s[0], s[2], out, states), todo))
    bad = 0
    for name, ok, line in res:
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name:24} {line}")
    named = out / "_scenes"
    named.mkdir(exist_ok=True)
    shots = []
    for n, ok, _ in res:
        if ok:
            (named / f"{n}.png").write_bytes((out / n / "scene.png").read_bytes())
            shots.append(str(named / f"{n}.png"))
    if shots:
        subprocess.run([sys.executable, "-X", "utf8", str(Path(SKILL) / "scripts" / "sheet.py"), *shots,
                        "--out", str(out / "scenes.png")], check=False)
    print(f"{len(res) - bad}/{len(res)} scenes reached")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
