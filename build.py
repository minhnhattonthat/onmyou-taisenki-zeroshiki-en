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
import enfont  # noqa: E402
import evscript  # noqa: E402
import font  # noqa: E402
import gfx  # noqa: E402
import signs  # noqa: E402
import cutin  # noqa: E402
import marker  # noqa: E402
import vwf  # noqa: E402
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
        self.layout = []  # (text id, address the game reads its first byte from), for build/strings.tsv
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


def install_engine(img):
    """English font glyphs over the fullwidth codes (tools/enfont.py) + the dialogue VWF (tools/vwf.py)."""
    for ch, code in enfont.CODES.items():
        if ch != " ":
            img.write(font.glyph_offset(img.orig, code), font.encode(enfont.glyph(ch)), f"font {ch!r}")
    vwf.install(img, img.write)
    gfx.install(img, img.write)


# Pointer tables whose strings are used as data by some reader: that reader gets a copy of the table + the original
# JP strings, so translating the table leaves it working. (table offset, literal-pool words of that reader, why)
# (The battle super-move cut-in used to get a JP copy of techniques_b here; tools/cutin.py now gives it a table of
# cell codes in the same place and size, and draws the names in English.)
JP_COPIES = []


def keep_jp_tables(img):
    """Copy each JP_COPIES table (entries = consecutive words pointing at JP strings) and its strings into free
    space, and point the listed literals at the copy."""
    for table, lits, why in JP_COPIES:
        ptrs = []
        while True:
            p = struct.unpack_from("<I", img.orig, table + 4 * len(ptrs))[0]
            if not 0x08000000 <= p < 0x08000000 + len(img.orig) or img.orig[p - 0x08000000] < 0x81:
                break
            ptrs.append(p - 0x08000000)
        blob, at = bytearray(), {}
        for p in ptrs:
            if p not in at:
                at[p] = len(blob)
                end = img.orig.index(b"\0", p)
                blob += img.orig[p:end + 1] + b"\0" * ((-(end + 1 - p)) % 2)
        new = img.alloc(4 * len(ptrs) + len(blob))
        base = new + 4 * len(ptrs)
        img.write(new, b"".join(struct.pack("<I", 0x08000000 | (base + at[p])) for p in ptrs) + bytes(blob),
                  f"jp copy {table:06X}")
        img.repoint(lits, new, f"jp copy {table:06X} ptr")


def text_runs(off, toks, at, new_toks):
    """(text id, built address) per text run of the script at off (id = the run's original offset), placed at `at`
    with new_toks (same token layout as toks: overrides only change text)."""
    out, p, q = [], off, at
    for t, n in zip(toks, new_toks):
        if t[0] == "text":
            out.append((p, q))
        p += len(evscript.encode([t]))
        q += len(evscript.encode([n]))
    return out


def build(orig, relocate=False, scripts=None, strings=None, engine=False, layout=None):
    """Return (rom bytes, write log). scripts/strings: optional {offset: tokens} / {offset: bytes} overrides.
    engine: install the English font + VWF (off for the identity tests). layout: a list to receive
    (text id, built address of its first byte) for every script run and table string."""
    img = Image(orig)
    if layout is not None:
        img.layout = layout
    if engine:
        install_engine(img)
        keep_jp_tables(img)
        cutin.install_names(img, img.write)
    sc =evscript.Scripts(orig)
    for off, toks in sorted(sc.scripts.items()):
        if off not in sc.refs:
            continue  # dead bare /999
        new_toks = (scripts or {}).get(off, toks)
        at = place(img, off, evscript.encode(new_toks) + b"\0", sc.room[off], sc.refs[off], f"script {off:06X}",
                   relocate, evscript.PINNED.get(off, ()))
        img.layout += text_runs(off, toks, at, new_toks)
    st = strtab.Strings(orig)
    for off, raw in sorted(st.strings.items()):
        raw = (strings or {}).get(off, raw)
        img.layout.append((off, place(img, off, raw + b"\0", st.room[off], st.refs[off], f"string {off:06X}",
                                      relocate)))
    if engine:
        # last, so a tileset that has to move takes free space after every string (string addresses stay put)
        signs.install(img, img.write)
        cutin.install(img, img.write)
    if len(img.buf) > len(orig):  # grow to a whole MiB, 0xFF filled
        img.buf += b"\xff" * ((-len(img.buf)) % 0x100000)
    return bytes(img.buf), img.log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--relocate-all", action="store_true")
    ap.add_argument("--marker", action="store_true", help="every entry = [id] marker text (tools/marker.py)")
    ap.add_argument("--no-engine", action="store_true", help="leave out the English font + VWF")
    ap.add_argument("--qa", action="append", default=[], metavar="ID=TEXT",
                    help="override one entry's en (width-gate stress lines; \\n = newline); output build/qa.gba")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    check_rom.check()
    orig = ROM.read_bytes()
    files = marker.markers(textdb.load()) if a.marker else None
    if a.qa:
        files = files or textdb.load()
        qa = dict(q.split("=", 1) for q in a.qa)
        for entries in files.values():
            for e in entries:
                if e["id"] in qa:
                    e["en"] = qa.pop(e["id"]).replace("\\n", "\n")
        if qa:
            raise SystemExit(f"--qa: no entry {', '.join(qa)}")
        a.out = a.out or str(OUT.with_name("qa.gba"))
    scripts, strings = textdb.overrides(orig, files)
    layout = []
    rom, log = build(orig, relocate=a.relocate_all, scripts=scripts, strings=strings, engine=not a.no_engine,
                     layout=layout)
    a.out = a.out or str(OUT.with_name("marker.gba") if a.marker else OUT)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(rom)
    out.with_suffix(".writes").write_text("".join(x + "\n" for x in log), encoding="utf-8")
    if out == OUT:  # textcover.py input: id<TAB>GBA address the game reads the text's first byte from
        out.with_name("strings.tsv").write_text(
            "".join(f"{i:06X}\t{0x08000000 | at:08X}\n" for i, at in sorted(layout)), encoding="utf-8")
    sha = hashlib.sha1(rom).hexdigest()
    same = "identical to the original" if rom == orig else f"{len(log)} writes"
    print(f"{out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {len(rom):#x} bytes, sha1 {sha}, {same}")


if __name__ == "__main__":
    main()
