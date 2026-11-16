"""Title logo in English (tools/titlelogo.py, docs/decisions.md D13)."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import titlelogo as t  # noqa: E402

pytestmark = pytest.mark.skipif(not build.ROM.exists(), reason="no ROM dump")


def test_resources_match_the_table():
    rom = build.ROM.read_bytes()
    for n, (off, objs) in t.RES.items():
        ptr = rom.find(struct.pack("<I", 0x08000000 | off), 0x403D00, 0x403D40)
        assert ptr > 0, f"{n}: no table entry"
        assert struct.unpack_from("<I", rom, ptr + 4)[0] == t.size(objs), f"{n}: size"


def test_every_resource_changes_and_keeps_its_size():
    rom = build.ROM.read_bytes()
    new, old = t.build(rom), t.build(rom, orig=True)
    for n, (off, objs) in t.RES.items():
        assert old[n] == rom[off:off + t.size(objs)]
        assert len(new[n]) == len(old[n])
        assert new[n] != old[n], f"{n} unchanged"
        assert max(new[n]) < len(t.PAL), f"{n}: palette index outside the logo's 64"


def test_each_word_sits_in_its_own_sprites():
    """The intro reveals 零, then 式, then the ribbon: ZERO must be whole in 零, SHIKI whole in 式."""
    rom = build.ROM.read_bytes()
    new = t.build(rom)
    gold = {t.I[c] for c in t.GOLD}
    for n, lo, hi in (("rei", 62, 102), ("shiki", 120, 160)):
        objs = t.RES[n][1]
        px = t.decode8(new[n], objs)
        xs = [x for y in range(t.H) for x in range(t.W) if t.covered(objs, x, y) and px[y][x] in gold]
        assert xs and lo <= min(xs) and max(xs) < hi, n
    ribbon = t.decode8(new["ribbon"], t.RES["ribbon"][1])
    rib = [x for y in range(t.H) for x in range(102, 120) if ribbon[y][x] in gold]
    assert not rib, "letters in the ribbon gap would show only after the ribbon appears"


def test_built_rom_holds_the_logo():
    orig = build.ROM.read_bytes()
    rom, _ = build.build(orig, engine=True)
    for n, data in t.build(orig).items():
        off = t.RES[n][0]
        assert rom[off:off + len(data)] == data, n
