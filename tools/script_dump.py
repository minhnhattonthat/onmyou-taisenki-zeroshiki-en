"""Print event scripts by id as opcodes with Japanese text collapsed (or shown with --text).

    python -X utf8 tools/script_dump.py 1001 1004 [--text] [--rom ROM]

Opcodes are split on `/`; each text run prints as <N chars> unless --text. Ids are StartScript ids
(tools/script_index.py). Recon helper for the debug tool (docs/re/debug.md).
"""
import argparse
import re

from script_index import ROM, TABLES, ptr, u32
from pathlib import Path

SJIS = rb"(?:[\x81-\x9f\xe0-\xef][\x40-\xfc])+"


def locate(d, sid):
    for lo, hi, base in TABLES:
        if lo <= sid <= hi:
            return ptr(d, u32(d, ptr(d, u32(d, base + (sid - lo) * 4))))
    raise SystemExit(f"no table for id {sid}")


def dump(d, off, text):
    end = d.find(b"/999", off)
    blob = d[off:end + 4]
    if text:
        s = re.sub(SJIS, lambda m: ("«" + m.group().decode("cp932", "replace") + "»").encode("utf-8"), blob)
        s = s.decode("utf-8", "replace")
    else:
        s = re.sub(SJIS, lambda m: b"<" + str(len(m.group()) // 2).encode() + b">", blob).decode("latin1")
    return s.replace("/", "\n/").strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+", type=lambda s: int(s, 0))
    ap.add_argument("--text", action="store_true")
    ap.add_argument("--rom", default=str(ROM))
    ap.add_argument("--offset", action="store_true", help="ids are file offsets, not script ids")
    a = ap.parse_args()
    d = Path(a.rom).read_bytes()
    for sid in a.ids:
        off = sid if a.offset else locate(d, sid)
        print(f"===== {sid} @ {off:06X}")
        print(dump(d, off, a.text))


if __name__ == "__main__":
    main()
