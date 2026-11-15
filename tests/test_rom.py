import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba"


@pytest.mark.skipif(not ROM.exists(), reason="no ROM dump")
def test_rom_matches_pin():
    want = (ROOT / "rom.sha1").read_text(encoding="utf-8").split("\n")[1].split()[0]
    assert hashlib.sha1(ROM.read_bytes()).hexdigest() == want


def test_tbl_module_imports():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import tbl  # noqa: F401
