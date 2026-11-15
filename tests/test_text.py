"""Phase 4 extract: script/*.json matches the ROM, every entry re-encodes to its original bytes, the text areas are
fully covered, and build.py's `en` path gives the original ROM when `en` = `jp`."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import evscript  # noqa: E402
import strtab  # noqa: E402
import textdb  # noqa: E402

pytestmark = pytest.mark.skipif(not build.ROM.exists(), reason="no ROM dump")


@pytest.fixture(scope="module")
def orig():
    return build.ROM.read_bytes()


@pytest.fixture(scope="module")
def files():
    return textdb.load()


def strip(files):
    return {n: [{k: v for k, v in e.items() if k not in textdb.KEEP} for e in es] for n, es in files.items()}


def test_json_is_in_sync_with_the_rom(orig, files):
    assert strip(files) == strip(textdb.dump_all(orig))


def test_every_entry_roundtrips(orig, files):
    n = 0
    for name, entries in files.items():
        for e in entries:
            off = int(e["id"], 16)
            if name.startswith("str_"):
                raw = textdb.encode_str(e["jp"])
                assert orig[off:off + len(raw) + 1] == raw + b"\0", e["id"]
            else:
                raw = evscript.encode_text(e["jp"])
                assert orig[off:off + len(raw)] == raw and orig[off + len(raw)] in (0, 0x2F), e["id"]
            n += 1
    assert n == 5185


def test_ids_cover_every_run_and_string(orig, files):
    ids = {e["id"] for es in files.values() for e in es}
    sc, st = evscript.Scripts(orig), strtab.Strings(orig)
    runs = {f"{pos:06X}" for _, _, pos, _, _ in textdb.runs(sc)}
    assert sum(1 for t in sc.scripts.values() for x in t if x[0] == "text") == len(runs) == 2191
    assert ids == runs | {f"{o:06X}" for o in st.strings}
    assert len(ids) == sum(map(len, files.values())), "duplicate id"


def test_text_areas_fully_covered(orig):
    assert textdb.uncovered(orig) == []


def test_en_equal_to_jp_builds_the_original(orig, files):
    filled = copy.deepcopy(files)
    for es in filled.values():
        for e in es:
            e["en"] = e["jp"]
    scripts, strings = textdb.overrides(orig, filled)
    assert len(strings) == 2994 and scripts
    rom, log = build.build(orig, scripts=scripts, strings=strings)
    assert log == [] and rom == orig


def test_en_replaces_one_run(orig, files):
    filled = {name: [dict(x, en="") for x in es] for name, es in files.items()}  # only this one run is English
    e = filled["ev_420000"][0]
    e["en"] = "あ{0010}"
    scripts, _ = textdb.overrides(orig, filled)
    rom, _ = build.build(orig, scripts=scripts)
    off = int(e["id"], 16)
    assert rom[off:off + 7] == "あ".encode("cp932") + b"0010/"


def test_stale_jp_is_refused(orig, files):
    bad = copy.deepcopy(files)
    bad["str_system"][0]["jp"] += "あ"
    with pytest.raises(ValueError, match="jp doesn't match"):
        textdb.overrides(orig, bad)


def test_dump_keeps_english(orig, tmp_path, monkeypatch):
    monkeypatch.setattr(textdb, "DIR", tmp_path)
    assert textdb.dump(orig) == (57, 57)
    p = tmp_path / "str_save.json"
    body = json.loads(p.read_text(encoding="utf-8"))
    body["entries"][0]["en"] = "Save"
    p.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    assert textdb.dump(orig) == (0, 57)            # existing files untouched
    textdb.dump(orig, force=True)
    assert textdb.load()["str_save"][0]["en"] == "Save"


def test_pad_width_guess():
    assert textdb.pad_width("この私に立ち向かうとは　　　面白い！") == 14
    assert textdb.pad_width("我は負けぬ！") is None
