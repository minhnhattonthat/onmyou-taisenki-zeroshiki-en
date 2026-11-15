"""Event-script codec and region model (docs/re/text.md, docs/re/scripts.md).

A script is ASCII bytecode with inline Shift-JIS text, ended by a NUL byte:
  `/NNN` + a fixed-length ASCII argument string (ARGS), then, if the next byte is neither `/` nor NUL, a text run:
  Shift-JIS characters and 4-char hex control codes (`0000` newline, `0010` page, `00C8` player name ...).
After the NUL the game pads with NULs to a 4-byte boundary. Scripts are reached through a u32 "slot" that sits right
before most scripts (tables point at slots, slots point at scripts), or straight from a table (tutorial scripts).

Tokens: ("op", "073", "0001") and ("text", "...") where text holds the decoded characters, control codes as `{0010}`
and any Shift-JIS pair that does not roundtrip through cp932 as `[XXXX]`. encode(parse()) is byte-exact.

    python -X utf8 tools/evscript.py [ROM]      # walk every script region, print counts, check the roundtrip
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "rom" / "Onmyou Taisenki Zeroshiki (Japan).gba"

# Argument length (ASCII chars after the 3-digit opcode). Read from every occurrence of each opcode followed by `/`
# or NUL in all script regions: every opcode has exactly one length (tools/evscript.py arglens checks this).
ARGS = {}
for _n, _ops in [
    (0, "022 024 026 037 042 045 046 058 059 060 065 072 077 078 080 081 082 085 086 091 106 142 143 224 225 226 "
        "230 231 233 235 236 240 999"),
    (4, "017 034 047 053 073 074 084 095 099 119 122 124 128 130 133 140 222 227 228 232 239"),
    (8, "012 014 036 048 054 079 093 094 098 121 125 136"),
    (12, "015 018 029 083 087 117 134 144 229"),
    (16, "013 035 070 135 141"),
    (20, "123"), (28, "129"), (32, "055"), (40, "052"), (52, "116"),
]:
    for _o in _ops.split():
        ARGS[_o] = _n

HEX = b"0123456789ABCDEFabcdef"
TOKEN = re.compile(r"\{([0-9A-Fa-f]{4})\}|\[([0-9A-Fa-f]{4})\]|(.)", re.S)

# Script regions: (start, end) file offsets. Region A holds map scripts, the id tables and the event scripts;
# region T holds the battle-tutorial scripts. Everything inside walks cleanly as slots/tables, scripts and NUL pad.
REGIONS = {"main": (0x419300, 0x46A104), "tutorial": (0x6918E8, 0x693978)}

# Scripts that must stay right after their slot: {script: [words that point at the slot]}. Code 0x0801DC90 loads
# [0x6918E8] (= slot 0x6918F0) and scans forward byte by byte to the first `/` (0x0801DD32), while 0x08027FB8
# dereferences the same word twice. A relocated build missed this and the shikigami-talk scene read the vacated
# room (tools/debug/stale_reads.py). Such a script moves together with a fresh slot; these words point at it.
PINNED = {0x6918F4: [0x6918E8]}


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC


def parse(d, p):
    """Parse the script at p. Returns (tokens, end) with end at the terminating NUL."""
    toks = []
    while True:
        b = d[p]
        if b == 0:
            return toks, p
        if b != 0x2F:
            raise ValueError(f"script byte {b:02X} at {p:06X}, expected / or NUL")
        op = d[p + 1:p + 4].decode("latin1")
        if op not in ARGS:
            raise ValueError(f"unknown opcode /{op} at {p:06X}")
        n = ARGS[op]
        arg = d[p + 4:p + 4 + n].decode("latin1")
        toks.append(("op", op, arg))
        p += 4 + n
        out = []
        while d[p] not in (0x2F, 0):
            b = d[p]
            if is_lead(b):
                pair = bytes(d[p:p + 2])
                try:
                    ch = pair.decode("cp932")
                    if ch.encode("cp932") != pair or ch in "{}[]":
                        raise UnicodeError
                except UnicodeError:
                    ch = f"[{pair.hex().upper()}]"
                out.append(ch)
                p += 2
            elif b in HEX:
                code = d[p:p + 4]
                if len(code) < 4 or any(c not in HEX for c in code):
                    raise ValueError(f"bad control code {code!r} at {p:06X}")
                out.append("{" + code.decode("ascii") + "}")
                p += 4
            else:
                raise ValueError(f"text byte {b:02X} at {p:06X}")
        if out:
            toks.append(("text", "".join(out)))


def encode_text(s):
    out = bytearray()
    for m in TOKEN.finditer(s):
        if m.group(1):
            out += m.group(1).encode("ascii")
        elif m.group(2):
            out += bytes.fromhex(m.group(2))
        else:
            out += m.group(3).encode("cp932")
    return bytes(out)


def encode(toks):
    """Script bytes without the NUL terminator."""
    out = bytearray()
    for t in toks:
        if t[0] == "op":
            if len(t[2]) != ARGS[t[1]]:
                raise ValueError(f"/{t[1]} wants {ARGS[t[1]]} arg chars, got {t[2]!r}")
            out += b"/" + t[1].encode("ascii") + t[2].encode("ascii")
        else:
            out += encode_text(t[1])
    return bytes(out)


def stored(body):
    """Bytes a script takes in the ROM: body, NUL, NUL pad to 4 (relative to a 4-aligned start)."""
    return body + b"\0" * (4 - len(body) % 4)


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def is_ptr(v):
    """ROM pointer, or the EWRAM 0x0200A000 the id tables use for empty slots."""
    return 0x08000000 <= v < 0x09000000 or 0x02000000 <= v < 0x02040000


def walk(d, lo, hi):
    """Split [lo, hi) into ("P", a, b) aligned pointer runs, ("S", a, b) scripts (b = NUL) and ("Z", a, b) NULs."""
    items, p = [], lo
    while p < hi:
        if p % 4 == 0 and is_ptr(u32(d, p)):
            q = p
            while q < hi and q % 4 == 0 and is_ptr(u32(d, q)):
                q += 4
            items.append(("P", p, q))
        elif d[p] == 0x2F:
            _, q = parse(d, p)
            items.append(("S", p, q))
        elif d[p] == 0:
            q = p + 1
            while q < hi and d[q] == 0 and not (q % 4 == 0 and is_ptr(u32(d, q))):
                q += 1
            items.append(("Z", p, q))
        else:
            raise ValueError(f"unexpected byte {d[p]:02X} at {p:06X} in script region")
        p = q
    return items


class Scripts:
    """Every script in every region, with the pointer words that reach it.

    scripts: {offset: tokens}; room: {offset: bytes the script may take in place (body + NUL + pad)};
    refs: {offset: [pointer word locations]} (slots and tutorial table entries; tables point at slots, which never move).
    """

    def __init__(self, d):
        self.scripts, self.room, self.refs = {}, {}, {}
        for name, (lo, hi) in REGIONS.items():
            items = walk(d, lo, hi)
            for i, (k, a, b) in enumerate(items):
                if k != "S":
                    continue
                self.scripts[a] = parse(d, a)[0]
                nxt = items[i + 1] if i + 1 < len(items) else ("Z", b, b + 1)
                self.room[a] = (nxt[2] if nxt[0] == "Z" else b + 1) - a
            starts = set(self.scripts)
            for k, a, b in items:
                if k == "P":
                    for w in range(a, b, 4):
                        t = u32(d, w) - 0x08000000
                        if t in starts:
                            self.refs.setdefault(t, []).append(w)
        # A bare `/999` with no pointer (0x41F840) is dead padding: it stays put and is never edited.
        missing = [a for a in self.scripts if a not in self.refs and self.scripts[a] != [("op", "999", "")]]
        if missing:
            raise ValueError(f"scripts with no pointer: {[hex(a) for a in missing[:8]]}")


def arglens(d):
    """{op: set(lengths)} from every op followed by / or NUL: each set must hold exactly ARGS[op]."""
    out = {}
    for lo, hi in REGIONS.values():
        for m in re.finditer(rb"/(\d\d\d)([0-9A-Fa-f\-]*)(?=[/\x00])", d[lo:hi]):
            out.setdefault(m.group(1).decode(), set()).add(len(m.group(2)))
    return out


def main():
    d = (Path(sys.argv[1]) if len(sys.argv) > 1 else ROM).read_bytes()
    s = Scripts(d)
    bad = [a for a, t in s.scripts.items() if encode(t) != d[a:a + len(encode(t))] or d[a + len(encode(t))] != 0]
    texts = sum(1 for t in s.scripts.values() for x in t if x[0] == "text")
    chars = sum(len(re.sub(r"\{....\}", "", x[1])) for t in s.scripts.values() for x in t if x[0] == "text")
    print(f"{len(s.scripts)} scripts, {sum(map(len, s.refs.values()))} pointer words, {texts} text runs, "
          f"~{chars} chars; roundtrip failures: {len(bad)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
