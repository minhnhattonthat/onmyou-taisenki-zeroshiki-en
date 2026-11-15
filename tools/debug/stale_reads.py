"""Reads of vacated text rooms in a --relocate-all build: text some code still reaches by its old address.

    python -X utf8 build.py --relocate-all --out work/reloc/reloc.gba
    python -X utf8 tools/debug/warp_all.py work/reloc/reloc.gba --out work/qa/reloc --states work/reloc/states \
        --probe tools/debug/romreads.lua
    python -X utf8 tools/debug/stale_reads.py work/reloc/reloc.writes work/qa/reloc

Rooms come from the build's write log (lines tagged "vacated"); reads from each scene's log.txt (romreads.lua
`R ADDR PC fN` lines). Prints one line per stale read (scene, address, PC, the room's owner). Exit 1 if any.
"""
import bisect

# Known reads that are the game's own behaviour, not a missed pointer: (lo, hi, pc, why)
EXPECTED = [
    (0x12B024, 0x12B02A, "08011258", "boot copies 5 halfwords of each of the 80 shikigami names (table 0x12AEE0) "
     "to RAM 0x020027B0+i*16 without stopping at NUL; entry 79 is the empty string 0x12B020, so it runs on into "
     "0x12B024. The original does the same."),
]
import re
import sys
from pathlib import Path


def main():
    writes, out = Path(sys.argv[1]), Path(sys.argv[2])
    rooms = []
    for line in writes.read_text(encoding="utf-8").splitlines():
        if line.endswith("vacated"):
            off, old, new, who = line.split(" ", 3)
            rooms.append((int(off, 16), int(off, 16) + len(old) // 2, who.rsplit(" ", 1)[0]))
    rooms.sort()
    starts = [r[0] for r in rooms]
    bad, n = 0, 0
    for log in sorted(out.glob("*/log.txt")):
        for m in re.finditer(r"^R ([0-9A-F]{8}) ([0-9A-F]{8}) f(\d+)", log.read_text(encoding="utf-8"), re.M):
            n += 1
            a = int(m.group(1), 16) & 0x1FFFFFF
            i = bisect.bisect_right(starts, a) - 1
            if any(lo <= a < hi and pc == m.group(2) for lo, hi, pc, _ in EXPECTED):
                continue
            if i >= 0 and rooms[i][0] <= a < rooms[i][1]:
                bad += 1
                print(f"{log.parent.name}: read {a:06X} pc {m.group(2)} f{m.group(3)} in vacated {rooms[i][2]}")
    print(f"{n} distinct reads checked, {len(rooms)} vacated rooms, {bad} stale")
    sys.exit(1 if bad or not n else 0)


if __name__ == "__main__":
    main()
