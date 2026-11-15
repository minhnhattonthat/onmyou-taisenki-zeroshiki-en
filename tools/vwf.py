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
import re
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


WSTATE = 0x0203FF20    # window VWF state: last n, last string, next x, y (16 bytes)
WIN_ORIG = {
    0x0029F0: "f0b557464e464546e0b489b088460004",  # prologue, replaced by the thunk
    0x002A16: "56d1",                              # bne: odd x -> return -1 (the plotter handles odd x)
}

# Window glyph routine 0x080029F0(flag, win): draws string[n] (n = [[win+0x20]], string = [win+0x1C], halfwords
# byte-swapped) at x = [win+4], y = [win+6]. Its 4 callers set x/y from a 14-cell grid; this prologue replaces them
# with a pixel cursor when the call follows the previous one (n = last n + 1, same string). Line start x = the
# window's base x [win+0x12]. Code NEWLINE moves to the next line and returns 1 (the caller counts it as drawn).
WIN_SRC = """
    push {{r0, r1, r4, r5, r6, r7, lr}}
    ldr r7, wstate
    ldr r2, [r1, #0x20]
    ldr r2, [r2]
    ldr r3, [r1, #0x1c]
    lsls r4, r2, #1
    ldrh r4, [r3, r4]
    lsrs r5, r4, #8
    lsls r4, r4, #24
    lsrs r4, r4, #16
    orrs r4, r5
    cmp r4, #0
    beq passthru
    ldr r5, [r7, #0]
    adds r5, #1
    cmp r5, r2
    bne adopt
    ldr r5, [r7, #4]
    cmp r5, r3
    bne adopt
    ldr r5, [r7, #8]
    ldr r6, [r7, #12]
    b have
adopt:
    ldrh r5, [r1, #4]
    ldrh r6, [r1, #6]
have:
    str r2, [r7, #0]
    str r3, [r7, #4]
    ldr r3, nlcode
    cmp r4, r3
    beq newline
    ldr r3, base
    subs r3, r4, r3
    ldr r0, ncodes
    cmp r3, r0
    bhs w16
    ldr r0, widths
    ldrb r3, [r0, r3]
    b wgot
w16:
    movs r3, #16
wgot:
    adds r0, r5, r3
    ldrh r4, [r1, #0x12]
    adds r4, #{span}
    cmp r0, r4
    ble fits
    ldrh r5, [r1, #0x12]
    adds r6, #16
    adds r0, r5, r3
fits:
    strh r5, [r1, #4]
    strh r6, [r1, #6]
    str r0, [r7, #8]
    str r6, [r7, #12]
passthru:
    pop {{r0, r1, r4, r5, r6, r7}}
    pop {{r2}}
    mov lr, r2
    push {{r4, r5, r6, r7, lr}}
    mov r7, sl
    mov r6, sb
    mov r5, r8
    push {{r5, r6, r7}}
    sub sp, #0x24
    mov r8, r1
    lsls r0, r0, #16
    ldr r2, back
    bx r2
newline:
    ldrh r5, [r1, #0x12]
    adds r6, #16
    str r5, [r7, #8]
    str r6, [r7, #12]
    pop {{r0, r1, r4, r5, r6, r7}}
    movs r0, #1
    pop {{r2}}
    bx r2

    .align 2
back:   .word 0x08002A01
wstate: .word {wstate:#x}
nlcode: .word {nl:#x}
base:   .word 0x8140
ncodes: .word {ncodes:#x}
widths: .word {widths:#x}
"""
WIN_SPAN = 224  # 14 cells of 16 px: the grid the game lays window text on


def win_code(far, widths_addr):
    addr = 0x08000000 | far
    src = WIN_SRC.format(span=WIN_SPAN, wstate=WSTATE, nl=enfont.NEWLINE, ncodes=NCODES,
                         widths=0x08000000 | widths_addr)
    return _asm(src, addr), addr


STRIP_ORIG = {  # the glyph-strip line renderers (docs/re/font.md "Renderer catalogue"), replaced by thunks
    0x0235D4: "f0b581b00549064a89180d68041c0026",  # 0x080235D4(str): 28 cells, intro scroll
    0x023E3C: "f0b581b00649074a89180c68051c0026",  # 0x08023E3C(str): 30 cells, staff credits
    0x03A168: "f0b557464e464546e0b40004060c0904",  # 0x0803A168(x, y, pal, map, dest, base, str): + tile map
}

# Strip renderers copy one whole 16x16 glyph (128 bytes, tiles TL TR BL BR) per character into the buffer
# [0x0201DE48] (VRAM, e.g. 0x06008020: plot by halfword, a byte store would land in both bytes), cell k at k*128; the game's tile map shows the cells left to right. The replacement clears the
# cells, then plots each glyph's pixels at a pixel cursor across the cells (cell = X / 16), advancing by WIDTHS.
STRIP_SRC = """
    b strip28
    b strip30
    b mapline
strip28:
    movs r2, #28
    b strip
strip30:
    movs r2, #30
strip:
    push {{lr}}
    ldr r1, bufp
    ldr r1, [r1]
    bl line
    movs r0, #1
    pop {{r1}}
    bx r1

@ 0x0803A168(x, y, pal, map, [sp]=tile dest, [sp+4]=tile base, [sp+8]=string) -> next free tile address
mapline:
    push {{r4, r5, r6, r7, lr}}
    lsls r0, r0, #16
    asrs r0, r0, #15
    adds r4, r3, r0
    lsls r1, r1, #16
    asrs r1, r1, #10
    adds r4, r4, r1
    lsls r5, r2, #28
    lsrs r5, r5, #16
    ldr r6, [sp, #20]
    ldr r7, [sp, #24]
    ldr r0, [sp, #28]
    adds r1, r6, #0
    movs r2, #0
    bl line
    adds r0, #15
    lsrs r0, r0, #4
    beq mdone
    subs r1, r6, r7
    lsls r1, r1, #16
    lsrs r1, r1, #21
    orrs r1, r5
    lsls r2, r0, #7
    adds r6, r6, r2
mloop:
    strh r1, [r4]
    adds r1, #1
    strh r1, [r4, #2]
    adds r1, #1
    adds r2, r4, #0
    adds r2, #0x40
    strh r1, [r2]
    adds r1, #1
    strh r1, [r2, #2]
    adds r1, #1
    adds r4, #4
    subs r0, #1
    bne mloop
mdone:
    adds r0, r6, #0
    pop {{r4, r5, r6, r7}}
    pop {{r1}}
    bx r1

@ line(string, dest, cells): clear `cells` 128-byte cells at dest (0 = as many as the string's width needs), plot
@ the string across them; returns its width in px.
line:
    push {{r4, r5, r6, r7, lr}}
    mov r4, r8
    mov r5, sb
    mov r6, sl
    mov r7, fp
    push {{r4, r5, r6, r7}}
    sub sp, #8
    mov r8, r0
    mov sb, r1
    cmp r2, #0
    bne lclr
    bl measure
    adds r0, #15
    lsrs r2, r0, #4
lclr:
    lsls r3, r2, #4
    mov fp, r3
    movs r0, #0
    mov sl, r0
    cmp r2, #0
    beq loop
    lsls r2, r2, #5
    movs r3, #5
    lsls r3, r3, #24
    orrs r2, r3
    mov r1, sb
    str r0, [sp]
    mov r0, sp
    svc #0xb
loop:
    mov r0, r8
    ldrb r4, [r0]
    cmp r4, #0
    beq done
    ldrh r4, [r0]
    adds r0, #2
    mov r8, r0
    lsrs r5, r4, #8
    lsls r4, r4, #24
    lsrs r4, r4, #16
    orrs r4, r5
    ldr r5, base
    subs r5, r4, r5
    ldr r6, ncodes
    cmp r5, r6
    bhs loop
    ldr r6, widths
    ldrb r6, [r6, r5]
    cmp r6, #0
    beq loop
    str r6, [sp, #4]
    ldr r1, k7ec0
    adds r1, r4, r1
    lsls r1, r1, #16
    asrs r1, r1, #16
    movs r0, #13
    ldr r3, lookup
    bl call_r3
    cmp r0, #0
    beq advance
    ldrh r1, [r0, #8]
    ldr r2, k0fff
    ands r1, r2
    lsls r1, r1, #16
    ldrh r2, [r0, #10]
    adds r1, r1, r2
    ldr r2, ftab
    ldr r2, [r2, #0x68]
    adds r7, r1, r2
    movs r5, #0
yl:
    movs r6, #0
cl:
    adds r0, r6, #0
    adds r1, r5, #0
    bl pixoff
    ldrb r2, [r7, r0]
    lsrs r2, r1
    movs r3, #15
    ands r2, r3
    beq next
    mov r0, sl
    adds r0, r0, r6
    cmp r0, fp
    bge next
    lsrs r4, r0, #4
    lsls r4, r4, #7
    movs r1, #15
    ands r0, r1
    adds r1, r5, #0
    bl pixoff
    adds r0, r0, r4
    add r0, sb
    movs r3, #1
    ands r3, r0
    lsls r3, r3, #3
    adds r1, r1, r3
    movs r3, #1
    bics r0, r3
    ldrh r3, [r0]
    lsls r2, r1
    movs r4, #15
    lsls r4, r1
    bics r3, r4
    orrs r3, r2
    strh r3, [r0]
next:
    adds r6, #1
    cmp r6, #16
    blt cl
    adds r5, #1
    cmp r5, #16
    blt yl
advance:
    ldr r0, [sp, #4]
    add sl, r0
    b loop
done:
    mov r0, sl
    add sp, #8
    pop {{r4, r5, r6, r7}}
    mov r8, r4
    mov sb, r5
    mov sl, r6
    mov fp, r7
    pop {{r4, r5, r6, r7}}
    pop {{r1}}
    bx r1
call_r3:
    bx r3
measure:
    push {{r4, r5, r6}}
    movs r6, #0
mloop2:
    ldrb r4, [r0]
    cmp r4, #0
    beq mend
    ldrh r4, [r0]
    adds r0, #2
    lsrs r5, r4, #8
    lsls r4, r4, #24
    lsrs r4, r4, #16
    orrs r4, r5
    ldr r5, base
    subs r4, r4, r5
    ldr r5, ncodes
    cmp r4, r5
    bhs mloop2
    ldr r5, widths
    ldrb r4, [r5, r4]
    adds r6, r6, r4
    b mloop2
mend:
    adds r0, r6, #0
    pop {{r4, r5, r6}}
    bx lr
pixoff:
    push {{r2, r3}}
    lsrs r2, r0, #3
    lsrs r3, r1, #3
    lsls r3, r3, #1
    adds r2, r2, r3
    lsls r2, r2, #5
    movs r3, #7
    ands r3, r1
    lsls r3, r3, #2
    adds r2, r2, r3
    movs r3, #7
    ands r3, r0
    lsrs r1, r3, #1
    adds r2, r2, r1
    movs r1, #1
    ands r1, r3
    lsls r1, r1, #2
    adds r0, r2, #0
    pop {{r2, r3}}
    bx lr

    .align 2
bufp:   .word 0x0201DE48
base:   .word 0x8140
ncodes: .word {ncodes:#x}
widths: .word {widths:#x}
k7ec0:  .word 0x7EC0
k0fff:  .word 0x0FFF
lookup: .word 0x080059A1
ftab:   .word 0x084028EC
"""


def strip_code(far, widths_addr):
    addr = 0x08000000 | far
    src = STRIP_SRC.format(ncodes=NCODES, widths=0x08000000 | widths_addr)
    return _asm(src, addr), addr, addr + 2, addr + 4


_IMM3 = re.compile(r"^\s*(adds|subs)\s+(r[0-7]),\s*(r[0-7]),\s*#(0x[0-9a-fA-F]+|\d+)", re.M)


def _asm(src, addr):
    # keystone silently mis-encodes `adds rd, rn, #imm` with rd != rn and imm > 7 (Thumb has 3 bits there)
    for m in _IMM3.finditer(src):
        if m.group(2) != m.group(3) and int(m.group(4), 0) > 7:
            raise ValueError(f"vwf asm: '{m.group(0).strip()}' needs imm <= 7 (use adds rd, #imm)")
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
    for off, hx in WIN_ORIG.items():
        b = bytes.fromhex(hx)
        assert orig[off:off + len(b)] == b, f"vwf: unexpected bytes at {off:06X}"
    wfar = img.alloc(len(win_code(0x800000, 0x800000)[0]) + 16)
    wcode, waddr = win_code(wfar, wt_off)
    write(wfar, wcode, "vwf window code")
    write(0x29F0, thunk(0x29F0, waddr), "vwf window thunk")
    write(0x2A16, b"\xc0\x46", "vwf window: allow odd x")
    for off, hx in STRIP_ORIG.items():
        b = bytes.fromhex(hx)
        assert orig[off:off + len(b)] == b, f"vwf: unexpected bytes at {off:06X}"
    sfar = img.alloc(len(strip_code(0x800000, 0x800000)[0]) + 16)
    scode, s28, s30, smap = strip_code(sfar, wt_off)
    write(sfar, scode, "vwf strip code")
    write(0x3A168, thunk(0x3A168, smap), "vwf strip thunk (map line 0x0803A168)")
    write(0x235D4, thunk(0x235D4, s28), "vwf strip thunk (intro scroll)")
    write(0x23E3C, thunk(0x23E3C, s30), "vwf strip thunk (credits)")
    return far


if __name__ == "__main__":
    code, e1, e2 = far_code(0x800000, 0x801000)
    print(f"far code {len(code)} bytes, entry1 {e1:08X}, entry2 {e2:08X}")
    assert STATE == (0x81 << 18) - 0x100
