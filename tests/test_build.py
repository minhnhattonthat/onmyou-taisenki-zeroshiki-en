"""Phase 3 identity build: unpack -> repack with no edits gives the original ROM byte for byte; the codecs roundtrip;
and moving every script and string to free space keeps every one reachable through its pointers."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import evscript  # noqa: E402
import strtab  # noqa: E402

pytestmark = pytest.mark.skipif(not build.ROM.exists(), reason="no ROM dump")


@pytest.fixture(scope="module")
def orig():
    return build.ROM.read_bytes()


def test_identity_build(orig):
    rom, log = build.build(orig)
    assert log == []
    assert rom == orig


def test_script_roundtrip(orig):
    sc = evscript.Scripts(orig)
    assert len(sc.scripts) == 541
    for off, toks in sc.scripts.items():
        body = evscript.encode(toks)
        assert orig[off:off + len(body)] == body and orig[off + len(body)] == 0, hex(off)
        assert len(body) + 1 <= sc.room[off]


def test_every_opcode_has_one_arg_length(orig):
    for op, lens in evscript.arglens(orig).items():
        assert op in evscript.ARGS, op
        assert lens == {evscript.ARGS[op]}, (op, lens)


def test_text_codec_escapes():
    s = "あ{0010}[8140]い"
    assert evscript.encode_text(s) == "あ".encode("cp932") + b"0010" + b"\x81\x40" + "い".encode("cp932")


def test_strings_found(orig):
    st = strtab.Strings(orig)
    assert len(st.strings) >= 2900
    assert not st.inner, "a pointer into the middle of a string: it can't move until that pointer is handled"
    for off, raw in st.strings.items():
        assert orig[off + len(raw)] == 0 and len(raw) + 1 <= st.room[off]


def test_string_room_stops_at_pointed_nuls(orig):
    # 0x40F73C (code 0x0810E1A2) is an empty string made of the NULs after "　カット" at 0x40F730; vacating it
    # drew ★ garbage over the battle tutorial in the first relocate-all run.
    st = strtab.Strings(orig)
    assert 0x40F730 + st.room[0x40F730] <= 0x40F73C


def test_relocate_all_keeps_everything_reachable(orig):
    rom, log = build.build(orig, relocate=True)
    sc, st = evscript.Scripts(orig), strtab.Strings(orig)
    for off, toks in sc.scripts.items():
        for loc in sc.refs.get(off, ()):
            new = struct.unpack_from("<I", rom, loc)[0] - 0x08000000
            assert new >= build.FREE[0]
            assert evscript.parse(rom, new)[0] == toks, hex(off)
    for off, raw in st.strings.items():
        for loc in st.refs[off]:
            new = struct.unpack_from("<I", rom, loc)[0] - 0x08000000
            assert new >= build.FREE[0] and rom[new:new + len(raw) + 1] == raw + b"\0", hex(off)


def test_layout_maps_every_text_to_its_built_address(orig):
    """build/strings.tsv (textcover.py input): each script run and table string id -> the address its first byte
    was built at; with everything relocated, the bytes there are the original text."""
    lay = []
    rom, _ = build.build(orig, relocate=True, layout=lay)
    assert len(lay) == len({i for i, _ in lay})
    for i, at in lay:
        assert at >= build.FREE[0], hex(i)
        assert rom[at:at + 2] == orig[i:i + 2], hex(i)


def test_pinned_script_moves_with_its_slot(orig):
    rom, _ = build.build(orig, relocate=True)
    for script, locs in evscript.PINNED.items():
        for loc in locs:
            slot = struct.unpack_from("<I", rom, loc)[0] - 0x08000000
            new = struct.unpack_from("<I", rom, slot)[0] - 0x08000000
            assert new == slot + 4 and rom[new] == 0x2F, hex(script)


def test_overflow_moves_only_the_grown_script(orig):
    sc = evscript.Scripts(orig)
    off = next(o for o, t in sorted(sc.scripts.items()) if any(x[0] == "text" for x in t) and o in sc.refs)
    toks = [(x[0], x[1] + "あ" * 200) if x[0] == "text" else x for x in sc.scripts[off]]
    rom, log = build.build(orig, scripts={off: toks})
    loc = sc.refs[off][0]
    new = struct.unpack_from("<I", rom, loc)[0] - 0x08000000
    assert new >= build.FREE[0] and evscript.parse(rom, new)[0] == toks
    assert rom[off:off + sc.room[off]] == b"\0" * sc.room[off]
    others = [o for o in sc.refs if o != off]
    assert all(rom[r:r + 4] == orig[r:r + 4] for o in others for r in sc.refs[o])


def test_cutin_keeps_japanese_keys(orig):
    """build.JP_COPIES: the battle super-move cut-in (0x08109614) still reads the JP techniques_b names after the
    table is translated; the shikigami page (literal 0x08036548) reads the English."""
    first = struct.unpack_from("<I", orig, 0x13BD78 + 4)[0] - 0x08000000
    en = b"\x82\x60\x82\x61\0"  # "ＡＢ" (English font codes)
    rom, _ = build.build(orig, strings={first: en}, engine=True)
    r32 = lambda b, o: struct.unpack_from("<I", b, o)[0] - 0x08000000  # noqa: E731
    menu, cutin = r32(rom, 0x36548), r32(rom, 0x10971C)
    assert menu == 0x13BD78 and cutin >= build.FREE[0]
    p_en, p_jp = r32(rom, menu + 4), r32(rom, cutin + 4)
    assert rom[p_en:p_en + len(en)] == en
    jp = orig[first:orig.index(b"\0", first) + 1]
    assert rom[p_jp:p_jp + len(jp)] == jp
    for k in range(76):  # every entry of the copy = the original string
        a, b = r32(orig, 0x13BD78 + 4 * k), r32(rom, cutin + 4 * k)
        assert rom[b:rom.index(b"\0", b)] == orig[a:orig.index(b"\0", a)], k
