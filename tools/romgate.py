"""romgate.py: the phase-7 ROM gate. Every byte the build changed must have a logged write behind it, and every
write must land where it is allowed.

    python -X utf8 tools/romgate.py [ROM]      # default build/onmyou_zeroshiki_en.gba + its .writes log

Checks (exit 1 on any failure, errors printed, a one-line summary otherwise):
  1. the skill's romdiff.py with the write log: each write's expected original bytes are in the original ROM, its
     new bytes are in the built ROM (not overwritten later), writes don't overlap, no changed byte lacks a write;
  2. text writes, structurally: `string X` / `script X` data only inside X's own room or in free space (0x800000+),
     `... vacated` only inside the room, `... ptr` only on a pointer word the extractor found for X (strtab /
     evscript refs, PINNED slots), and that word points at X's new home;
  3. every other write inside a range of tbl/allowed_ranges.txt;
  4. code hooks swallow no branch target: no Thumb B/Bcc/BL anywhere in 0..0x200000 and no literal word lands
     strictly inside a hook span marked `code` in allowed_ranges.txt, unless the branch sits inside the routine the
     hook replaces (listed as `dead=LO-HI` on that line).
tests/test_romgate.py runs it on a fresh build.
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import evscript  # noqa: E402
import strtab  # noqa: E402
from skill import SCRIPTS  # noqa: E402

sys.path.insert(0, SCRIPTS)
import romdiff  # noqa: E402

RANGES = ROOT / "tbl" / "allowed_ranges.txt"
FREE = 0x800000
CODE_END = 0x200000  # Thumb code + literal pools of the original sit below this


def load_ranges(path=RANGES):
    """[(lo, hi_inclusive, is_code, [(dead_lo, dead_hi)], reason)]"""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        body, _, reason = line.partition("#")
        if not body.strip():
            continue
        lo, hi = (int(x, 16) for x in body.split()[0].split("-"))
        dead = [tuple(int(x, 16) for x in m.groups()) for m in re.finditer(r"dead=([0-9A-Fa-f]+)-([0-9A-Fa-f]+)", reason)]
        out.append((lo, hi, reason.strip().startswith("code"), dead, reason.strip()))
    return out


def parse_log(lines):
    out = []
    for line in lines:
        parts = line.split(None, 3)
        if parts:
            out.append((int(parts[0], 16), bytes.fromhex(parts[1]), bytes.fromhex(parts[2]), parts[3].strip()))
    return out


TEXT = re.compile(r"(string|script) ([0-9A-F]{6})( slot ptr| slot| ptr| vacated)?$")


def text_errors(orig, new, writes):
    st, sc = strtab.Strings(orig), evscript.Scripts(orig)
    room = {("string", k): v for k, v in st.room.items()} | {("script", k): v for k, v in sc.room.items()}
    refs = {("string", k): set(v) for k, v in st.refs.items()} | {("script", k): set(v) for k, v in sc.refs.items()}
    pinned = {("script", k): set(v) for k, v in evscript.PINNED.items()}
    home, slot = {}, {}
    for off, _, data, who in writes:
        m = TEXT.match(who)
        if m and m.group(3) is None:
            home[(m.group(1), int(m.group(2), 16))] = off if off >= FREE else int(m.group(2), 16)
        elif m and m.group(3) == " slot":
            slot[(m.group(1), int(m.group(2), 16))] = off
    errs, n = [], 0
    for off, _, data, who in writes:
        m = TEXT.match(who)
        if not m:
            continue
        n += 1
        key, kind = (m.group(1), int(m.group(2), 16)), m.group(3)
        start, end = key[1], key[1] + room.get(key, 0)
        inside = start <= off and off + len(data) <= end
        if key not in room:
            errs.append(f"{off:06X}: {who}: no such {key[0]} in the original")
        elif kind is None and not (inside or off >= FREE):
            errs.append(f"{off:06X}: {who}: data outside its room {start:06X}..{end:06X} and below free space")
        elif kind == " vacated" and not inside:
            errs.append(f"{off:06X}: {who}: vacated bytes outside its room")
        elif kind == " slot" and off < FREE:
            errs.append(f"{off:06X}: {who}: new slot below free space")
        elif kind in (" ptr", " slot ptr"):
            ok = pinned.get(key, set()) if kind == " slot ptr" else refs.get(key, set())
            want = slot.get(key) if kind == " slot ptr" else home.get(key)
            got = struct.unpack_from("<I", new, off)[0] - 0x08000000
            if off not in ok or len(data) != 4:
                errs.append(f"{off:06X}: {who}: not a pointer word the extractor found for this {key[0]}")
            elif got != want:
                errs.append(f"{off:06X}: {who}: points at {got:06X}, the {key[0]} lives at {want}")
    return errs, n


def branch_targets(rom, end=CODE_END):
    """[(source offset, target offset)] of every Thumb B/Bcc/BL in a linear sweep, + literal words (|1 or even)."""
    out = []
    hw = struct.unpack_from(f"<{end // 2}H", rom, 0)
    for i, h in enumerate(hw):
        pc = 2 * i + 4
        if h >> 12 == 0xD and (h >> 8) & 0xF < 0xE:
            out.append((2 * i, pc + ((h & 0xFF) ^ 0x80) * 2 - 0x100))
        elif h >> 11 == 0x1C:
            out.append((2 * i, pc + ((h & 0x7FF) ^ 0x400) * 2 - 0x800))
        elif h >> 11 == 0x1E and i + 1 < len(hw) and hw[i + 1] >> 11 == 0x1F:
            hi = ((h & 0x7FF) ^ 0x400) - 0x400
            out.append((2 * i, pc + (hi << 12) + ((hw[i + 1] & 0x7FF) << 1)))
    for i in range(0, end, 4):
        w = struct.unpack_from("<I", rom, i)[0]
        if 0x08000000 <= w < 0x08000000 + end:
            out.append((i, (w & ~1) - 0x08000000))
    return out


def code_errors(orig, ranges):
    errs = []
    targets = branch_targets(orig)
    for lo, hi, is_code, dead, reason in ranges:
        if not is_code:
            continue
        for src, t in targets:
            if lo < t <= hi and not lo <= src <= hi and not any(a <= src <= b for a, b in dead):
                errs.append(f"{src:06X} -> {t:06X}: branch or literal lands inside hook {lo:06X}-{hi:06X} ({reason})")
    return errs


def gate(orig, new, log_lines, ranges=None):
    """Return (errors, summary)."""
    ranges = load_ranges() if ranges is None else ranges
    writes = parse_log(log_lines)
    errs, ok = romdiff.check(orig, new, set(), writes)
    terrs, ntext = text_errors(orig, new, writes)
    errs += terrs
    other = 0
    for off, _, data, who in writes:
        if TEXT.match(who):
            continue
        other += 1
        if not any(lo <= off and off + len(data) - 1 <= hi for lo, hi, *_ in ranges):
            errs.append(f"{off:06X}+{len(data)}: {who}: outside tbl/allowed_ranges.txt")
    errs += code_errors(orig, ranges)
    return errs, f"{len(writes)} writes ({ntext} text, {other} engine/font), {ok} changed bytes, all accounted for"


def main():
    rom = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "onmyou_zeroshiki_en.gba"
    sys.path.insert(0, str(ROOT))
    import build
    orig = build.ROM.read_bytes()
    errs, summary = gate(orig, rom.read_bytes(), rom.with_suffix(".writes").read_text(encoding="utf-8").splitlines())
    for e in errs[:80]:
        print(e)
    if errs:
        sys.exit(f"romgate: {len(errs)} errors")
    print(f"romgate ok: {summary}")


if __name__ == "__main__":
    main()
