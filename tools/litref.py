"""Find Thumb `ldr rX, [pc, #imm]` instructions that load a given literal word.

    python -X utf8 tools/litref.py ROM WORD [WORD...] [--end 0x120000]

Prints the file offset of each loading instruction and of its literal. Use it to find every user of a RAM
variable (e.g. 0x0000E7BC, an offset the code adds to a base register) or an absolute address.
"""
import argparse
import struct


def find(rom, word, end):
    hits = []
    pat = struct.pack("<I", word)
    pos = rom.find(pat, 0, end)
    while pos != -1:
        if pos % 4 == 0:
            # Thumb ldr literal: 01001 rrr iiiiiiii, target = (pc & ~3) + 4 + imm*4, pc = instr addr
            for back in range(4, 1024 + 4, 2):
                ins = pos - back
                if ins < 0:
                    break
                hw = rom[ins] | rom[ins + 1] << 8
                if hw >> 11 == 0b01001 and ((ins & ~3) + 4 + (hw & 0xFF) * 4) == pos:
                    hits.append((ins, pos, (hw >> 8) & 7))
        pos = rom.find(pat, pos + 1, end)
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("words", nargs="+")
    ap.add_argument("--end", default="0x120000")
    a = ap.parse_args()
    rom = open(a.rom, "rb").read()
    for w in a.words:
        hits = find(rom, int(w, 16), int(a.end, 16))
        print("%s: %d loads" % (w, len(hits)))
        for ins, lit, reg in hits:
            print("  %08X ldr r%d  (literal %06X)" % (0x08000000 + ins, reg, lit))


if __name__ == "__main__":
    main()
