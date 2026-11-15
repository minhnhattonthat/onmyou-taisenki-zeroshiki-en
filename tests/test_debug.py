"""Debug-tool inputs: every scene in tools/debug/scenes.txt is well formed and names a script the ROM has."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from script_index import ROM, scripts  # noqa: E402

KINDS = {"boot", "top", "field", "script", "raw"}


def scene_lines():
    for line in (ROOT / "tools" / "debug" / "scenes.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            yield line.split()


def test_scenes_well_formed():
    names = set()
    for name, kind, *rest in scene_lines():
        assert kind in KINDS, name
        assert name not in names, f"duplicate scene {name}"
        names.add(name)
        for tok in rest:
            if tok.startswith("press="):
                for step in tok[6:].split("|"):
                    assert re.fullmatch(r"\d+:[a-z+\-]+", step), f"{name}: bad press step {step}"
            if tok.startswith("flags="):
                for f in tok[6:].split(","):
                    assert re.fullmatch(r"\d+(=[01])?", f) and int(f.split("=")[0]) < 2048, f"{name}: bad flag {f}"
    assert len(names) >= 40


@pytest.mark.skipif(not ROM.exists(), reason="needs the original ROM")
def test_script_scenes_exist():
    have = {sid for sid, *_ in scripts(ROM.read_bytes())}
    for name, kind, *rest in scene_lines():
        if kind == "script":
            assert int(rest[0]) in have, f"{name}: no script {rest[0]}"
