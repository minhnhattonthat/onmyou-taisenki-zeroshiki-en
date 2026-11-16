"""Phase 7 ROM gate (tools/romgate.py) on a fresh English build, and proof that it catches each kind of stray write."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import romgate  # noqa: E402
import textdb  # noqa: E402

pytestmark = pytest.mark.skipif(not build.ROM.exists(), reason="no ROM dump")


@pytest.fixture(scope="module")
def built():
    orig = build.ROM.read_bytes()
    scripts, strings = textdb.overrides(orig, None)
    rom, log = build.build(orig, scripts=scripts, strings=strings, engine=True)
    return orig, rom, log


def test_english_build_passes_the_gate(built):
    errs, _ = romgate.gate(*built)
    assert errs == []


def test_relocate_all_passes_the_gate():
    orig = build.ROM.read_bytes()
    rom, log = build.build(orig, relocate=True)
    errs, _ = romgate.gate(orig, rom, log)
    assert errs == []


def test_unlogged_change_fails(built):
    orig, rom, log = built
    bad = bytearray(rom)
    bad[0x100] ^= 0xFF
    errs, _ = romgate.gate(orig, bytes(bad), log)
    assert any("outside writes" in e for e in errs)


def test_write_outside_allowed_ranges_fails(built):
    orig, rom, log = built
    bad = bytearray(rom)
    bad[0x100] ^= 0xFF
    line = f"000100 {orig[0x100]:02x} {bad[0x100]:02x} stray engine write"
    errs, _ = romgate.gate(orig, bytes(bad), log + [line])
    assert any("outside tbl/allowed_ranges.txt" in e for e in errs)


def test_pointer_write_on_a_foreign_word_fails(built):
    orig, rom, log = built
    ptr = next(x for x in log if x.split(None, 3)[3].startswith("string ") and x.endswith(" ptr"))
    other = next(x for x in log if x.split(None, 3)[3].startswith("string ") and x.endswith(" ptr")
                 and x.split()[2] != ptr.split()[2])
    off, old, new, who = ptr.split(None, 3)
    forged = " ".join([other.split()[0], other.split()[1], other.split()[2], who])  # other's word, claimed by ptr
    errs, _ = romgate.gate(orig, rom, [x for x in log if x != other] + [forged])
    assert any("not a pointer word the extractor found" in e for e in errs)


def test_branch_into_a_code_hook_fails(built):
    orig, rom, log = built
    # without its dead= exemption, the speaker-plate hook has the replaced loop's back-edge 0x0801EE28 -> 0x0801ED6E
    ranges = [(lo, hi, code, [] if lo == 0x01ED64 else dead, why) for lo, hi, code, dead, why in romgate.load_ranges()]
    errs, _ = romgate.gate(orig, rom, log, ranges)
    assert any(e.startswith("01EE28 -> 01ED6E") for e in errs)
