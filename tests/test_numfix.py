"""Battle messages built as name + number + suffix: the number goes at the name's end, not at the JP name's
byte length (vwf.num_patch; "Atta21down!" / "Bo16 damage!" / a level number inside "Now at level")."""
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import vwf  # noqa: E402

pytestmark = pytest.mark.skipif(not build.ROM.exists(), reason="no ROM dump")


def _bl_target(rom, off):
    hi, lo = struct.unpack_from("<HH", rom, off)
    assert hi >> 11 == 0x1E and lo >> 11 == 0x1F
    v = ((hi & 0x7FF) << 11) | (lo & 0x7FF)
    if v & (1 << 21):
        v -= 1 << 22
    return 0x08000000 + off + 4 + 2 * v


def test_number_calls_go_to_the_nul_scanner():
    orig = build.ROM.read_bytes()
    img = bytearray(orig)

    def write(off, data, who):
        img[off:off + len(data)] = data

    vwf.num_patch(orig, write)
    back = {}
    for k, imm in ((0, 6), (4, 4), (8, 0x22)):  # each entry starts with subs r2, #imm
        assert struct.unpack_from("<H", img, (vwf.NUM_FN & 0xFFFFFF) + k)[0] == 0x3A00 | imm
        back[imm] = vwf.NUM_FN + k
    for off, n, _ in vwf.NUM_CALLS:
        assert _bl_target(orig, off) == vwf.NUM_WRITER
        assert _bl_target(img, off) == back[n]


def test_shikigami_page_strings_drawn_as_one_line():
    orig = build.ROM.read_bytes()
    img = bytearray(orig)

    def write(off, data, who):
        img[off:off + len(data)] = data

    vwf.num_patch(orig, write)
    vwf.join_patch(orig, write)
    for first, later, kind, _ in vwf.JOIN_CALLS:
        assert _bl_target(img, first) == vwf.JOIN_FN + (0 if kind == "clan" else 10)
        for off in later:
            assert img[off:off + 4] == b"\x00\x20\xc0\x46"  # movs r0, #0; nop: drawn by join


def test_stat_names_carry_their_own_spaces():
    en = {e["id"]: e["en"] for e in json.loads((ROOT / "script/str_battle_msgs.json").read_text(encoding="utf-8"))
          ["entries"]}
    for sid in ("40D7B4", "40D964", "40D9DC", "40D9E8", "40D9F4", "40DA00", "40E3B4"):
        assert en[sid].endswith(" "), sid      # name + number / name + shikigami
    for sid in ("40D970", "40DC30", "40E330"):
        assert en[sid].startswith(" "), sid    # number + suffix
