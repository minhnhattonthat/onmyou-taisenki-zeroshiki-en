"""Town shop signs (tools/signs.py, graphics survey G11): every sign is redrawn and lands in the built tilesets."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import lzscan  # noqa: E402
import signs  # noqa: E402

pytestmark = pytest.mark.skipif(not build.ROM.exists(), reason="no ROM dump")


def test_every_sign_changes_its_tiles():
    rom = build.ROM.read_bytes()
    for name, (idx, grid, draw) in signs.SIGNS.items():
        data = signs.block(rom, idx)[2]
        before = signs.decode(data, grid)
        after = signs.decode(data, grid)
        draw(after)
        assert after != before, f"sign {name} draws nothing"


def test_built_tilesets_hold_the_new_tiles():
    orig = build.ROM.read_bytes()
    rom, _ = build.build(orig, engine=True)
    swap = signs.changes(orig)
    seen = set()
    for idx in signs.TOWN:
        hdr = struct.unpack_from("<I", rom, signs.TABLE + 4 * idx)[0] & 0x1FFFFFF
        assert rom[hdr:hdr + 4] == orig[signs.block(orig, idx)[0]:][:4], f"tileset {idx}: header"
        new = lzscan.lz77_decompress(rom, hdr + 4)[0]
        old = signs.block(orig, idx)[2]
        assert len(new) == len(old)
        for t in range(len(old) // 32):
            o = signs.tile(old, t)
            assert signs.tile(new, t) == swap.get(o, o), f"tileset {idx} tile {t:X}"
            if o in swap:
                seen.add(o)
    assert seen == set(swap), "a changed tile is in no town tileset"
