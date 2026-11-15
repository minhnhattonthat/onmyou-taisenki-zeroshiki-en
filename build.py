"""build.py: rebuild the ROM from its unpacked text (event scripts + string tables).

Text comes from script/*.json (tools/textdb.py): an entry with a non-empty `en` replaces its run or string.

    python -X utf8 build.py                  # -> build/onmyou_zeroshiki_en.gba (+ .writes log for romdiff.py)
    python -X utf8 build.py --relocate-all   # stress test: move every script and string past 8 MiB, repoint all

Packing rule: a script or string that still fits its original room is written in place (rest of the room NUL);
one that doesn't moves to free space (FREE, 0x800000.., the ROM grows) and every pointer word to it is rewritten.
Scripts are reached only through slot words (tables point at slots, slots never move), strings through the pointer
words tools/strtab.py collects. With no edits everything fits, so the output must equal the original byte for
byte (tests/test_build.py, phase 3 "identity build"). --relocate-all fills the vacated rooms with 0xFF so any
read that skips the new pointers shows up as garbage in the emulator.
"""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import check_rom  # noqa: E402
import evscript  # noqa: E402
import strtab  # noqa: E402
import textdb  # noqa: E402

ROM = ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba"
OUT = ROOT / "build" / "onmyou_zeroshiki_en.gba"
FREE = (0x800000, 0x1000000)  # past the 8 MiB original; EEPROM carts address up to 16 MiB of ROM


class Image:
    """Output buffer that logs every write (romdiff.py --writes format) and hands out free space."""

    def __init__(self, orig):
        self.orig = orig
        self.buf = bytearray(orig)
        self.log = []
        self.free = FREE[0]

    def write(self, off, data, who):
        end = off + len(data)
        if end > len(self.buf):
            self.buf += b"\xff" * (end - len(self.buf))
        old = bytes(self.orig[off:end]).ljust(len(data), b"\xff")
        if old != data:
            self.log.append(f"{off:06X} {old.hex()} {bytes(data).hex()} {who}")
        self.buf[off:end] = data

    def alloc(self, size, align=4):
        self.free = (self.free + align - 1) // align * align
        off = self.free
        self.free += size
        if self.free > FREE[1]:
            sys.exit(f"out of free space: need {size} bytes at {off:06X}")
        return off

    def repoint(self, locs, target, who):
        for loc in locs:
            self.write(loc, struct.pack("<I", 0x08000000 | target), who)


def place(img, start, data, room, refs, who, relocate, slot_refs=()):
    """data includes its terminator; room is what it may take in place. slot_refs: words that must point at a
    slot sitting right before the data (evscript.PINNED); a moved pinned script gets a fresh slot."""
    if len(data) <= room and not relocate:
        img.write(start, data + b"\0" * (room - len(data)), who)
        return start
    pad = (-len(data)) % 4
    if slot_refs:
        slot = img.alloc(4 + len(data) + pad)
        new = slot + 4
        img.write(slot, struct.pack("<I", 0x08000000 | new), f"{who} slot")
        img.repoint(slot_refs, slot, f"{who} slot ptr")
    else:
        new = img.alloc(len(data) + pad)
    img.write(new, data + b"\0" * pad, who)
    img.repoint(refs, new, f"{who} ptr")
    img.write(start, b"\xff" * room if relocate else b"\0" * room, f"{who} vacated")
    return new


def build(orig, relocate=False, scripts=None, strings=None):
    """Return (rom bytes, write log). scripts/strings: optional {offset: tokens} / {offset: bytes} overrides."""
    img = Image(orig)
    sc = evscript.Scripts(orig)
    for off, toks in sorted(sc.scripts.items()):
        if off not in sc.refs:
            continue  # dead bare /999
        toks = (scripts or {}).get(off, toks)
        place(img, off, evscript.encode(toks) + b"\0", sc.room[off], sc.refs[off], f"script {off:06X}", relocate,
              evscript.PINNED.get(off, ()))
    st = strtab.Strings(orig)
    for off, raw in sorted(st.strings.items()):
        raw = (strings or {}).get(off, raw)
        place(img, off, raw + b"\0", st.room[off], st.refs[off], f"string {off:06X}", relocate)
    if len(img.buf) > len(orig):  # grow to a whole MiB, 0xFF filled
        img.buf += b"\xff" * ((-len(img.buf)) % 0x100000)
    return bytes(img.buf), img.log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--relocate-all", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    check_rom.check()
    orig = ROM.read_bytes()
    scripts, strings = textdb.overrides(orig)
    rom, log = build(orig, relocate=a.relocate_all, scripts=scripts, strings=strings)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(rom)
    out.with_suffix(".writes").write_text("".join(x + "\n" for x in log), encoding="utf-8")
    sha = hashlib.sha1(rom).hexdigest()
    same = "identical to the original" if rom == orig else f"{len(log)} writes"
    print(f"{out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {len(rom):#x} bytes, sha1 {sha}, {same}")


if __name__ == "__main__":
    main()
