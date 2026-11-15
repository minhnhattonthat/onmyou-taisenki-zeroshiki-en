"""VWF for the dialogue renderer (docs/re/font.md "VWF"). Assembled with keystone; build.py installs it.

The game draws dialogue one 16x16 glyph at a time with 0x08002F88(buf, code, idx, 0x1C, [sp]=stride arg), which
places the glyph at the cell idx (x = (idx % 14) * 16 + 8, y = idx / 14 * 16). Callers: the wrapper 0x08002F68
(script text 0x0802DE96, text variables 0x0801E068) and the string drawer 0x080144F4 (padded quote strings,
BL at 0x08014526). The patch:
  * vwf_pos (free space) keeps a pixel cursor in STATE: a call whose idx follows the last one in the same buffer
    goes at the cursor; any other idx starts where the game would put it (row/col from idx, idx >= 64 = line 2).
    The cursor advances by the code's width (table WIDTHS, 1 byte per code 0x8140..0x987F); a glyph that would
    cross RIGHT wraps to the next line; the code NEWLINE (no glyph) starts a new line.
  * 0x08002F68 and 0x08002F78 become trampolines to the far entries (the second takes the BL from 0x08014526).
  * 0x08002FFE..0x08003028 in the draw routine reads x/y from STATE instead of dividing idx by 14.
  * the script newline code {0000} sets idx = 64 instead of 14 (0x0802DD36), so a 13-character first line can't
    look sequential.
"""
import struct
import sys
from pathlib import Path

import keystone

sys.path.insert(0, str(Path(__file__).resolve().parent))
import enfont  # noqa: E402

STATE = 0x0203FF00     # 24 bytes of EWRAM: last idx, next x, last buf, x, y, (spare)
LINE2 = 64             # idx the newline code sets
LEFT = 8               # x of a line's first glyph (the game's own margin)
RIGHT = LEFT + 224     # a glyph may not start past RIGHT - its width
NCODES = 0x1740

ORIG = {  # offset: original bytes the patch replaces (asserted)
    0x002F68: "10b581b00904090c1b041b0ce2242401009400f005f801b010bc02bc0847",
    0x002FFE: "201c",
    0x014526: "eef72ffd",
    0x02DD36: "0e21",
}

FAR_SRC = """
    b entry1
    b entry2
entry1:
    push {{r4, lr}}
    sub sp, #4
    lsls r1, r1, #16
    lsrs r1, r1, #16
    lsls r3, r3, #16
    lsrs r3, r3, #16
    bl vwf_pos
    movs r4, #0xe2
    lsls r4, r4, #4
    str r4, [sp]
    ldr r4, draw
    bl call_r4
    add sp, #4
    pop {{r4}}
    pop {{r1}}
    bx r1
call_r4:
    bx r4

entry2:
    push {{r4, lr}}
    bl vwf_pos
    ldr r4, [sp, #4]
    mov lr, r4
    ldr r4, draw
    mov ip, r4
    pop {{r4}}
    add sp, #4
    bx ip

vwf_pos:
    push {{r4, r5, r6, r7, lr}}
    ldr r7, state
    lsls r4, r1, #16
    lsrs r4, r4, #24
    lsls r5, r1, #24
    lsrs r5, r5, #16
    orrs r4, r5
    ldr r5, nlcode
    cmp r4, r5
    bne not_nl
    ldr r5, [r7, #16]
    adds r5, #16
    str r5, [r7, #16]
    movs r5, #{left}
    str r5, [r7, #4]
    str r2, [r7, #0]
    str r0, [r7, #8]
    b done
not_nl:
    ldr r5, base
    subs r4, r4, r5
    ldr r5, ncodes
    cmp r4, r5
    bhs wdef
    ldr r5, widths
    ldrb r4, [r5, r4]
    b wgot
wdef:
    movs r4, #16
wgot:
    ldr r5, [r7, #0]
    adds r5, #1
    cmp r5, r2
    bne legacy
    ldr r5, [r7, #8]
    cmp r5, r0
    bne legacy
    ldr r6, [r7, #4]
    adds r5, r6, r4
    cmp r5, #{right}
    ble have
    movs r6, #{left}
    ldr r5, [r7, #16]
    adds r5, #16
    str r5, [r7, #16]
    b have
legacy:
    movs r5, #0
    adds r6, r2, #0
    cmp r6, #{line2}
    blt cols
    subs r6, #{line2}
    movs r5, #1
    b colsdone
cols:
    cmp r6, #14
    blt colsdone
    subs r6, #14
    adds r5, #1
    b cols
colsdone:
    lsls r6, r6, #4
    adds r6, #{left}
    lsls r5, r5, #4
    str r5, [r7, #16]
have:
    str r6, [r7, #12]
    adds r6, r6, r4
    str r6, [r7, #4]
    str r2, [r7, #0]
    str r0, [r7, #8]
done:
    pop {{r4, r5, r6, r7}}
    pop {{r4}}
    bx r4

    .align 2
draw:   .word 0x08002F89
state:  .word {state:#x}
nlcode: .word {nl:#x}
base:   .word 0x8140
ncodes: .word {ncodes:#x}
widths: .word {widths:#x}
"""


def _asm(src, addr):
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
    enc, _ = ks.asm(src, addr)
    return bytes(enc)


def thunk(addr, target):
    """16 bytes at addr (Thumb): bx pc / nop, then ARM ldr ip,[pc] / bx ip / .word target|1."""
    assert addr % 4 == 0
    return struct.pack("<HHIII", 0x4778, 0x46C0, 0xE59FC000, 0xE12FFF1C, target | 1)


def bl(addr, target):
    off = (target - (addr + 4)) >> 1
    assert -(1 << 21) <= off < (1 << 21)
    return struct.pack("<HH", 0xF000 | ((off >> 11) & 0x7FF), 0xF800 | (off & 0x7FF))


def widths():
    """One byte per code 0x8140..0x987F: English glyph widths, 16 elsewhere."""
    t = bytearray([16]) * NCODES
    for ch, code in enfont.CODES.items():
        t[code - 0x8140] = enfont.width(ch)
    t[enfont.NEWLINE - 0x8140] = 0
    return bytes(t)


def far_code(far, widths_addr):
    """Assemble the far blob for file offset `far` (4-aligned)."""
    addr = 0x08000000 | far
    src = FAR_SRC.format(left=LEFT, right=RIGHT, line2=LINE2, state=STATE, nl=enfont.NEWLINE, ncodes=NCODES,
                         widths=0x08000000 | widths_addr)
    code = _asm(src, addr)
    return code, addr, addr + 2  # the two leading branches


def install(img, write):
    """Install the VWF into an Image (build.py): allocate far code + width table, patch the hook sites.
    write(off, data, who) is the logging writer; img.alloc gives free space."""
    orig = img.orig
    for off, hx in ORIG.items():
        b = bytes.fromhex(hx)
        assert orig[off:off + len(b)] == b, f"vwf: unexpected bytes at {off:06X}"
    wt = widths()
    wt_off = img.alloc(len(wt))
    write(wt_off, wt, "vwf widths")
    size = len(far_code(0x800000, 0x800000)[0])
    far = img.alloc(size + 16)
    code, e1, e2 = far_code(far, wt_off)
    write(far, code, "vwf code")
    write(0x2F68, thunk(0x2F68, e1), "vwf thunk wrapper")
    write(0x2F78, thunk(0x2F78, e2), "vwf thunk strings")
    write(0x14526, bl(0x08014526, 0x08002F78), "vwf string drawer -> thunk")
    inner = _asm("movs r0, #0x81; lsls r0, r0, #18; subs r0, #0x80; subs r0, #0x80;"
                 "ldr r1, [r0, #12]; mov sl, r1; ldr r1, [r0, #16]; str r1, [sp, #0xc]", 0x08002FFE)
    inner += b"\xc0\x46" * ((0x3028 - 0x2FFE - len(inner)) // 2)
    assert len(inner) == 0x3028 - 0x2FFE
    write(0x2FFE, inner, "vwf x/y from state")
    write(0x2DD36, struct.pack("<H", 0x2100 | LINE2), "vwf newline idx")
    return far


if __name__ == "__main__":
    code, e1, e2 = far_code(0x800000, 0x801000)
    print(f"far code {len(code)} bytes, entry1 {e1:08X}, entry2 {e2:08X}")
    assert STATE == (0x81 << 18) - 0x100
