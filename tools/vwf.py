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
import ensmall  # noqa: E402

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
    0x014098: "f0b557464e464546e0b484b0061c0c98",  # 0x08014098(str, tile, size, flag, max): OBJ menu cells
    0x110BAC: "f0b557464e464546e0b481b000930b9d",  # 0x08110BAC: battle results, same args as 0x0803A168
    0x110C88: "f0b5474680b492b098461a9c0004050c",  # 0x08110C88: battle text rows, splits at 28 bytes
}

# Strip renderers copy one whole 16x16 glyph (128 bytes, tiles TL TR BL BR) per character into the buffer
# [0x0201DE48] (VRAM, e.g. 0x06008020: plot by halfword, a byte store would land in both bytes), cell k at k*128; the game's tile map shows the cells left to right. The replacement clears the
# cells, then plots each glyph's pixels at a pixel cursor across the cells (cell = X / 16), advancing by WIDTHS.
STRIP_SRC = """
    b strip28
    b strip30
    b mapline
    b menu
    b twoline
    b gridline
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

@ gridline: mapline's arguments, for the name-entry character grid (the BL at 0x0803AEB2 only): one 16 px cell per
@ character with the glyph centred in it, so cell k still shows character k (the cursor picks by index) and every
@ cell of the row is redrawn (no tiles left over from the previous tab).
gridline:
    push {{r4, r5, r6, r7, lr}}
    sub sp, #8
    lsls r0, r0, #16
    asrs r0, r0, #15
    adds r4, r3, r0
    lsls r1, r1, #16
    asrs r1, r1, #10
    adds r4, r4, r1
    lsls r5, r2, #28
    lsrs r5, r5, #16
    ldr r6, [sp, #28]
    ldr r7, [sp, #36]
gl_loop:
    ldrb r0, [r7]
    cmp r0, #0
    beq gl_done
    mov r1, sp
    strb r0, [r1]
    ldrb r0, [r7, #1]
    strb r0, [r1, #1]
    movs r0, #0
    strh r0, [r1, #2]
    mov r0, sp
    bl measure
    movs r3, #16
    subs r3, r3, r0
    asrs r3, r3, #1
    bpl gl_x
    movs r3, #0
gl_x:
    mov r0, sp
    adds r1, r6, #0
    movs r2, #1
    bl linex
    ldr r1, [sp, #32]
    subs r1, r6, r1
    lsls r1, r1, #16
    lsrs r1, r1, #21
    orrs r1, r5
    strh r1, [r4]
    adds r1, #1
    strh r1, [r4, #2]
    adds r1, #1
    adds r2, r4, #0
    adds r2, #0x40
    strh r1, [r2]
    adds r1, #1
    strh r1, [r2, #2]
    adds r4, #4
    adds r6, #128
    adds r7, #2
    b gl_loop
gl_done:
    adds r0, r6, #0
    add sp, #8
    pop {{r4, r5, r6, r7}}
    pop {{r1}}
    bx r1

@ 0x08014098(str, tile index, size, flag, [sp]=max) -> chars drawn. Size 16 + flag 0 (byte-swapped string): the
@ game copies one 16x16 glyph per char into OBJ tiles 0x06010000 + ((index + 4n) & 0x3FF) * 32 (1D, TL TR BL BR),
@ up to 28 chars or n <= max, and returns n. Here only the cells the string's pixel width needs are cleared and
@ plotted (no more than the JP's n while the English fits n*16 px, the width gate, so neighbouring fields' tiles
@ stay intact); returns that cell count. The
@ max argument is not applied: the width lint bounds English. Other modes (8 px font, flag != 0): original code.
menu:
    cmp r2, #16
    bne morig
    cmp r3, #0
    bne morig
    push {{lr}}
    lsls r1, r1, #22
    lsrs r1, r1, #17
    ldr r3, objvram
    adds r1, r1, r3
    movs r2, #0
    bl line
    adds r0, #15
    lsrs r0, r0, #4
    pop {{r1}}
    bx r1
morig:
    push {{r4, r5, r6, r7, lr}}
    mov r7, sl
    mov r6, sb
    mov r5, r8
    push {{r5, r6, r7}}
    sub sp, #0x10
    adds r6, r0, #0
    ldr r0, [sp, #0x30]
    push {{r0}}
    ldr r0, mback
    mov ip, r0
    pop {{r0}}
    bx ip

@ 0x08110C88(x, y, pal, map, [sp]=dest, [sp+4]=base, [sp+8]=str) -> next tile address: battle text box. The game
@ draws strings of <= 28 bytes on one line, else copies 28 bytes + the rest into a 60-byte stack buffer (a long
@ English line overran it) and draws them with 0x08110BAC on rows y and y+2. Here each row is the text up to the
@ newline code or up to 224 px (14 JP cells, so Japanese splits where it did), copied into a bounded buffer, then
@ drawn by mapline; row 2 continues after the split; anything past row 2 is dropped.
twoline:
    push {{r4, r5, r6, r7, lr}}
    sub sp, #140
    adds r4, r0, #0
    adds r5, r1, #0
    adds r6, r2, #0
    adds r7, r3, #0
    ldr r0, [sp, #160]
    str r0, [sp]
    ldr r0, [sp, #164]
    str r0, [sp, #4]
    add r2, sp, #12
    str r2, [sp, #8]
    ldr r1, [sp, #168]
    bl tl_seg
    str r0, [sp, #136]
    adds r0, r4, #0
    adds r1, r5, #0
    adds r2, r6, #0
    adds r3, r7, #0
    bl mapline
    ldr r1, [sp, #136]
    cmp r1, #0
    beq tl_ret
    ldrb r2, [r1]
    cmp r2, #0
    beq tl_ret
    str r0, [sp]
    add r2, sp, #12
    bl tl_seg
    adds r0, r4, #0
    adds r1, r5, #2
    adds r2, r6, #0
    adds r3, r7, #0
    bl mapline
tl_ret:
    add sp, #140
    pop {{r4, r5, r6, r7}}
    pop {{r1}}
    bx r1

@ tl_seg(r1 = string, r2 = buffer): copy halfword codes up to NUL, the newline code (skipped) or 224 px into the
@ buffer (<= 120 bytes + NUL); returns where the next row starts (0 at the end of the string).
tl_seg:
    push {{r4, r5, r6}}
    movs r3, #0
    movs r6, #0
ts_loop:
    ldrb r4, [r1]
    cmp r4, #0
    beq ts_end
    ldrb r5, [r1, #1]
    lsls r4, r4, #8
    orrs r4, r5
    ldr r5, nlcode2
    cmp r4, r5
    bne ts_ch
    adds r1, #2
    b ts_split
ts_ch:
    ldr r5, base
    subs r4, r4, r5
    ldr r5, ncodes
    cmp r4, r5
    bhs ts_w16
    ldr r5, widths
    ldrb r4, [r5, r4]
    b ts_w
ts_w16:
    movs r4, #16
ts_w:
    adds r6, r6, r4
    cmp r6, #224
    bgt ts_split
    cmp r3, #120
    bhs ts_next
    ldrb r4, [r1]
    strb r4, [r2, r3]
    adds r3, #1
    ldrb r4, [r1, #1]
    strb r4, [r2, r3]
    adds r3, #1
ts_next:
    adds r1, #2
    b ts_loop
ts_end:
    movs r1, #0
ts_split:
    movs r4, #0
    strb r4, [r2, r3]
    adds r0, r1, #0
    pop {{r4, r5, r6}}
    bx lr

@ line(string, dest, cells): clear `cells` 128-byte cells at dest (0 = as many as the string's width needs), plot
@ the string across them; returns its width in px. The newline code 0x81AD moves x to the first multiple of 224 px
@ (14 cells) that is >= x and > 0, so a row exactly 224 px wide doesn't skip a row: OBJ-cell texts laid out as rows of 14 cells (the shikigami page's ability description, tile 0x58).
@ linex = line with the start x in r3 (gridline centres one glyph in its cell).
line:
    movs r3, #0
linex:
    push {{r4, r5, r6, r7, lr}}
    mov r4, r8
    mov r5, sb
    mov r6, sl
    mov r7, fp
    push {{r4, r5, r6, r7}}
    sub sp, #12
    str r3, [sp, #8]
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
    ldr r3, [sp, #8]
    mov sl, r3
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
    ldr r5, nlcode2
    cmp r4, r5
    bne lchar
    movs r0, #224
lnl:
    cmp r0, sl
    bge lnlset
    adds r0, #224
    b lnl
lnlset:
    mov sl, r0
    b loop
lchar:
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
    add sp, #12
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
    ldr r5, nlcode2
    cmp r4, r5
    bne mchar
    movs r4, #224
mnl:
    cmp r4, r6
    bge mnlset
    adds r4, #224
    b mnl
mnlset:
    adds r6, r4, #0
    b mloop2
mchar:
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
nlcode2: .word {nl:#x}
objvram: .word 0x06010000
mback:  .word 0x080140A9
"""


TAG_ORIG = {  # the battle speaker name tag (docs/re/font.md "Battle name tag")
    0x111B50: "70b581b0051c6801134a85180c1c0026",  # 0x08111B50(tile, str): <= 5 small glyphs into OBJ tiles
    0x10F98A: "0bf0fdfe",                          # bl 0x0811B788 (byte count) -> tag x offset (10 - n) * 2
    0x110AE8: "f0b557464e464546e0b481b000930b9d",  # 0x08110AE8: small-font BG labels, one tile per char
    0x01ED64: "0020814600276d461e35381c68300b49",  # 0x0801EC54 dialogue speaker plate: 5-tile loop
}
PLATE_END = 0x0801EE2A  # first instruction after the plate's 5-tile loop (0x0801ED64..0x0801EE28)
# Widened speaker plate (docs/re/font.md "Speaker plate"): the BG frame grows from 6 to 8 map columns (x 8..71,
# interior x 10..69, centre x 40), the OBJ text from 32x8 + 8x8 to 32x8 + 32x8 (tiles 0x68..0x6F, OBJ x 12 + offset).
PLATE_TILES = 8
PLATE_PX = 56          # longest name drawn; interior is 60 px
PLATE_MID = 56         # text x offset from the OBJ's base x 12 = (PLATE_MID - width) / 2 -> centred on x 40
PLATE_GFX = 0x171E6C   # raw BG tiles of the window parts (resource 0x1B0E94): plate top 1..6, bottom 8..0xD
PLATE_MAPS = (0x19DE66, 0x19E1EA)  # raw 30-wide window maps: the plate's top row at col 1 (bottom row +60 bytes)
PLATE_CELL_PART2 = 0x3E7998       # sprite cell 2 frame 0 part 2 (x 12, y -4, attr, tile byte offset 0x80)
PLATE_BANDS = {0: (6, 7, 7, 8, 8), 1: (9, 9, 10, 10, 11)}  # fill colour per pixel row: top tiles rows 3..7, bottom 0..4
SMALL_N = 0x260   # codes in the small font (0x8140..0x839F)
# Battle name tag (sprite 0x2F, cell 2 = the speaker plate's 32x8 + 32x8): 8 free OBJ tiles, see tag_tiles.
TAG_TILE = 0x3D3
TAG_TILES = 8
TAG_LITERALS = (0x10F9DC, 0x120A80, 0x115754, 0x1157DC, 0x115E50, 0x1162F4)  # words 0x3DB loaded as the tile
TAG_FILL_CALLS = (0x1156EA, 0x115772, 0x115DE6, 0x116296)  # bl 0x08005354(2, tile): the 5-tile plain fill

TAG_SRC = """
    b tag
    b tagw
    b smapline
    b plate
    b fill7
@ fill7(r0 = resource type, r1 = tile): the battle tag's plain fill (resource 2 = 5 tiles of colour 1) loaded by
@ 0x08005354 at tile and tile + 2, so it covers 7 tiles (56 px, the widened tag; tile + 7 is left as the tag
@ code cleared it). Called from the four fill paths 0x081156EA/0x08115772/0x08115DE6/0x08116296.
fill7:
    push {{r4, r5, lr}}
    adds r4, r0, #0
    adds r5, r1, #0
    bl f7load
    adds r0, r4, #0
    adds r1, r5, #2
    bl f7load
    pop {{r4, r5}}
    pop {{r1}}
    bx r1
f7load:
    ldr r3, f7addr
    bx r3
    .align 2
f7addr: .word 0x08005355
@ plate(r0 = str) -> small pixel width capped at PLATE_PX: the dialogue speaker plate (0x0801EC54), OBJ tiles
@ 0x68..0x6F (0x06010D00; widened from 5 tiles, see plate_frame). ROM strings are byte-order Shift-JIS; RAM ones (player name 0x020025AE, 0x020027B0 + 16n) hold
@ native halfwords and are copied byte-swapped (<= 16 codes) first.
plate:
    push {{r4, r5, lr}}
    sub sp, #36
    adds r4, r0, #0
    lsrs r1, r0, #27
    bne pl_rom
    mov r1, sp
    movs r2, #0
pl_cp:
    ldrh r3, [r4, r2]
    cmp r3, #0
    beq pl_end
    lsrs r5, r3, #8
    lsls r3, r3, #24
    lsrs r3, r3, #16
    orrs r3, r5
    strh r3, [r1, r2]
    adds r2, #2
    cmp r2, #32
    blt pl_cp
pl_end:
    movs r3, #0
    strh r3, [r1, r2]
    mov r4, sp
pl_rom:
    adds r0, r4, #0
    ldr r1, plobj
    movs r2, #{platetiles}
    movs r3, #{platepx}
    bl splot
    cmp r0, #{platepx}
    ble pl_fit
    movs r0, #{platepx}
pl_fit:
    add sp, #36
    pop {{r4, r5}}
    pop {{r1}}
    bx r1

@ 0x08111B50(r0 = tile index, r1 = str): the tag's OBJ tiles (0x06010000 + index * 32, 1D) = splot(str, tiles,
@ TAG_TILES, TAG_PX). The index is TAG_TILE (moved from 0x3DB: see tag_tiles in install).
tag:
    push {{r4, lr}}
    lsls r4, r0, #5
    ldr r0, tobj
    adds r4, r4, r0
    adds r0, r1, #0
    adds r1, r4, #0
    movs r2, #{tagtiles}
    movs r3, #{tagpx}
    bl splot
    pop {{r4}}
    pop {{r0}}
    bx r0

@ 0x08110AE8(x, y, pal, map, [sp] dest, [sp+4] base, [sp+8] str) -> next free tile address: BG labels in the small
@ font. The game puts one tile per char at map (x + i, y), with no limit (a long string overwrote the tiles after
@ dest). Here: n = ceil(width / 8) tiles at dest = splot(str, dest, n, n * 8), map entries for those n tiles.
smapline:
    push {{r4, r5, r6, r7, lr}}
    lsls r0, r0, #1
    lsls r1, r1, #6
    adds r0, r0, r1
    adds r4, r3, r0
    lsls r5, r2, #12
    ldr r0, [sp, #28]
    bl smeasure
    adds r0, #7
    lsrs r6, r0, #3
    ldr r0, [sp, #28]
    ldr r1, [sp, #20]
    adds r2, r6, #0
    lsls r3, r6, #3
    bl splot
    ldr r7, [sp, #20]
smloop:
    cmp r6, #0
    beq smdone
    ldr r0, [sp, #24]
    subs r0, r7, r0
    lsrs r0, r0, #5
    orrs r0, r5
    strh r0, [r4]
    adds r4, #2
    adds r7, #32
    subs r6, #1
    b smloop
smdone:
    adds r0, r7, #0
    pop {{r4, r5, r6, r7}}
    pop {{r1}}
    bx r1

@ splot(r0 = str, r1 = dest tiles (8x8 4bpp, consecutive), r2 = tiles to clear, r3 = max px) -> width in px:
@ plot the string in the small font (type 12) at variable width (small width table), clipped to max px.
splot:
    push {{r4, r5, r6, r7, lr}}
    mov r4, r8
    mov r5, sb
    mov r6, sl
    mov r7, fp
    push {{r4, r5, r6, r7}}
    sub sp, #8
    mov r8, r0
    mov sb, r1
    mov fp, r3
    movs r0, #0
    mov sl, r0
    str r0, [sp]
    mov r0, sp
    lsls r2, r2, #3
    ldr r3, tclr
    orrs r2, r3
    svc #0xb
tloop:
    mov r0, r8
    ldrb r4, [r0]
    cmp r4, #0
    beq tdone
    ldrh r4, [r0]
    adds r0, #2
    mov r8, r0
    lsrs r5, r4, #8
    lsls r4, r4, #24
    lsrs r4, r4, #16
    orrs r4, r5
    ldr r5, tbase
    subs r5, r4, r5
    ldr r6, tncodes
    cmp r5, r6
    bhs tloop
    ldr r6, swidths
    ldrb r6, [r6, r5]
    cmp r6, #0
    beq tloop
    str r6, [sp, #4]
    ldr r0, tsmalln
    cmp r5, r0
    bhs tadv
    cmp r5, #0
    beq tadv
    ldr r1, tk7ec0
    adds r1, r4, r1
    lsls r1, r1, #16
    asrs r1, r1, #16
    movs r0, #12
    ldr r3, tlookup
    bl tcall_r3
    cmp r0, #0
    beq tadv
    ldrh r1, [r0, #8]
    ldr r2, tk0fff
    ands r1, r2
    lsls r1, r1, #16
    ldrh r2, [r0, #10]
    adds r1, r1, r2
    ldr r2, tftab
    ldr r2, [r2, #0x60]
    adds r7, r1, r2
    movs r5, #0
tyl:
    movs r6, #0
tcl:
    lsrs r0, r6, #1
    lsls r1, r5, #2
    adds r0, r0, r1
    ldrb r2, [r7, r0]
    movs r1, #1
    ands r1, r6
    lsls r1, r1, #2
    lsrs r2, r1
    movs r3, #15
    ands r2, r3
    beq tnext
    mov r0, sl
    adds r0, r0, r6
    cmp r0, fp
    bge tnext
    lsrs r4, r0, #3
    lsls r4, r4, #5
    lsls r1, r5, #2
    adds r4, r4, r1
    movs r1, #7
    ands r1, r0
    lsrs r3, r1, #1
    adds r4, r4, r3
    add r4, sb
    movs r3, #1
    ands r0, r3
    lsls r0, r0, #2
    ands r3, r4
    lsls r3, r3, #3
    adds r0, r0, r3
    movs r3, #1
    bics r4, r3
    ldrh r3, [r4]
    lsls r2, r0
    movs r1, #15
    lsls r1, r0
    bics r3, r1
    orrs r3, r2
    strh r3, [r4]
tnext:
    adds r6, #1
    cmp r6, #8
    blt tcl
    adds r5, #1
    cmp r5, #8
    blt tyl
tadv:
    ldr r0, [sp, #4]
    add sl, r0
    b tloop
tdone:
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
tcall_r3:
    bx r3

@ tagw(r0 = str) -> (small pixel width + 2) / 4 - 4 (signed), replacing the byte count at 0x0810F98A: the caller puts
@ the tag's OBJ at base x 12 + (10 - r0) * 2 = 40 - width / 2, so the text is centred on x 40 like the widened
@ speaker plate (same BG frame, interior x 10..69). Width capped at TAG_PX (what `tag` draws).
tagw:
    push {{lr}}
    bl smeasure
    cmp r0, #{tagpx}
    ble twfit
    movs r0, #{tagpx}
twfit:
    adds r0, #2
    lsrs r0, r0, #2
    subs r0, #4
    pop {{r1}}
    bx r1

@ smeasure(r0 = str) -> pixel width in the small font (r1-r3 untouched)
smeasure:
    push {{r4, r5, r6}}
    movs r6, #0
twl:
    ldrb r4, [r0]
    cmp r4, #0
    beq twe
    ldrh r4, [r0]
    adds r0, #2
    lsrs r5, r4, #8
    lsls r4, r4, #24
    lsrs r4, r4, #16
    orrs r4, r5
    ldr r5, tbase
    subs r4, r4, r5
    ldr r5, tncodes
    cmp r4, r5
    bhs twl
    ldr r5, swidths
    ldrb r4, [r5, r4]
    adds r6, r6, r4
    b twl
twe:
    adds r0, r6, #0
    pop {{r4, r5, r6}}
    bx lr

    .align 2
tobj:    .word 0x06010000
plobj:   .word 0x06010D00
tclr:    .word 0x05000000
tbase:   .word 0x8140
tncodes: .word {ncodes:#x}
tsmalln: .word {smalln:#x}
swidths: .word {swidths:#x}
tk7ec0:  .word 0x7EC0
tk0fff:  .word 0x0FFF
tlookup: .word 0x080059A1
tftab:   .word 0x084028EC
"""


def tag_code(far, swidths_addr):
    """Assemble the small-font blob at file offset `far`; returns (code, tag, tagw, smapline, plate entries)."""
    addr = 0x08000000 | far
    src = TAG_SRC.format(ncodes=NCODES, smalln=SMALL_N, swidths=0x08000000 | swidths_addr, tagpx=ensmall.TAG_PX,
                         tagtiles=TAG_TILES, platepx=PLATE_PX, platetiles=PLATE_TILES)
    return _asm(src, addr), addr, addr + 2, addr + 4, addr + 6, addr + 8


def tag_tiles(orig, write, fill7):
    """Move the battle name tag's OBJ tiles from 0x3DB (5 tiles; the shared sprite cell 2 is 64 px wide since
    plate_frame, so its right part showed the ground-shadow sprite's tiles 0x3E0..0x3E2) to TAG_TILE..+7, which no
    toured battle uses (tools/debug/vramfree.lua). Every literal 0x3DB belongs to sprite 0x2F (cell 2, palette 13):
    the tag's draw call and the sprite creations; the fill paths load resource 2 there through fill7."""
    for lit in TAG_LITERALS:
        assert orig[lit:lit + 4] == struct.pack("<I", 0x3DB), f"tag tile literal {lit:06X} moved"
        write(lit, struct.pack("<I", TAG_TILE), f"battle name tag tile 0x3DB -> {TAG_TILE:#x} (literal {lit:06X})")
    for site in TAG_FILL_CALLS:
        assert orig[site:site + 4] == bl(0x08000000 | site, 0x08005354), f"tag fill call {site:06X} moved"
        write(site, bl(0x08000000 | site, 0x08111B70), f"tag fill {site:06X}: resource 2 -> fill7 (7 tiles)")


def plate_patch(plate):
    """Inline code at 0x0801ED64 replacing the speaker plate's 5-tile loop: plot via `plate`, then make the caller's
    centring step (x += table[n] at [sp + 0x10 + 2n], table (0, 16, 12, 8, 4, 0) = (40 - 8n) / 2) centre by pixels:
    n = 1 and table[1] = (PLATE_MID - width) / 2 (width <= PLATE_PX = PLATE_MID, so never negative)."""
    src = f"""
    adds r0, r6, #0
    ldr r3, paddr
    bl pcall
    movs r1, #{PLATE_MID}
    subs r1, r1, r0
    asrs r1, r1, #1
    add r2, sp, #0x10
    strh r1, [r2, #2]
    movs r0, #1
    mov sb, r0
    b #{PLATE_END:#x}
pcall:
    bx r3
    .align 2
paddr: .word {plate | 1:#x}
"""
    code = _asm(src, 0x0801ED64)
    assert 0x0801ED64 + len(code) <= PLATE_END
    return code


def _plate_tile(t, bands, first_row):
    """Recolour one 4bpp tile's fill (palette 6..0xC, the original's diagonal gradient) to one colour per pixel row,
    so the plate's middle tiles become identical and can repeat."""
    out = bytearray(t)
    for y in range(8):
        k = y - first_row
        if not 0 <= k < len(bands):
            continue
        for x in range(8):
            o = y * 4 + x // 2
            sh = 4 * (x & 1)
            if 6 <= (out[o] >> sh) & 15 <= 0xC:
                out[o] = (out[o] & ~(15 << sh) & 0xFF) | (bands[k] << sh)
    return bytes(out)


def plate_frame(orig, write):
    """Widen the dialogue speaker plate's BG frame from 6 to 8 columns and its OBJ text from 40 to 64 px."""
    for i in range(1, 7):
        o = PLATE_GFX + i * 32
        write(o, _plate_tile(orig[o:o + 32], PLATE_BANDS[0], 3), f"speaker plate top tile {i}: banded fill")
    for i in range(8, 0xE):
        o = PLATE_GFX + i * 32
        write(o, _plate_tile(orig[o:o + 32], PLATE_BANDS[1], 0), f"speaker plate bottom tile {i}: banded fill")
    hw = lambda *v: b"".join(struct.pack("<H", x) for x in v)
    for p in PLATE_MAPS:
        assert orig[p:p + 18] == hw(1, 2, 3, 4, 5, 6, 0, 0, 0), f"plate map {p:06X} moved"
        # bottom row cols 1..6 = plate, 7..10 = the box border's decoration, 11.. plain border (dropped by the shift)
        b = p + 60
        bot = struct.unpack_from("<12H", orig, b)
        assert bot[:7] == (8, 9, 10, 11, 12, 13, 14) and bot[10] == bot[11], f"plate map {p:06X} bottom"
        write(p, hw(1, 2, 3, 4, 5, 5, 5, 6), f"speaker plate map {p:06X}: top row 8 columns")
        write(b, hw(8, 9, 10, 11, 12, 12, 12, 13, *bot[6:10]), f"speaker plate map {p:06X}: bottom row 8 columns")
    assert orig[PLATE_CELL_PART2:PLATE_CELL_PART2 + 8] == hw(12, 0xFFFC, 0, 0x80), "plate sprite cell moved"
    write(PLATE_CELL_PART2 + 4, hw(0x5000), "speaker plate sprite cell 2 part 2: 8x8 -> 32x8")


def strip_code(far, widths_addr):
    addr = 0x08000000 | far
    src = STRIP_SRC.format(ncodes=NCODES, widths=0x08000000 | widths_addr, nl=enfont.NEWLINE)
    return _asm(src, addr), addr, addr + 2, addr + 4, addr + 6, addr + 8, addr + 10


_IMM3 = re.compile(r"^\s*(adds|subs)\s+(r[0-7]),\s*(r[0-7]),\s*#(0x[0-9a-fA-F]+|\d+)", re.M)


_SPBH = re.compile(r"^\s*(ldr|str)(b|h|sb|sh)\s+r\d+,\s*\[sp\b.*$", re.M)


def _asm(src, addr):
    # keystone silently mis-encodes `adds rd, rn, #imm` with rd != rn and imm > 7 (Thumb has 3 bits there)
    for m in _IMM3.finditer(src):
        if m.group(2) != m.group(3) and int(m.group(4), 0) > 7:
            raise ValueError(f"vwf asm: '{m.group(0).strip()}' needs imm <= 7 (use adds rd, #imm)")
    # ... and turns a byte/halfword access through sp into a 32-bit Thumb-2 strb.w/ldrh.w the GBA can't run
    m = _SPBH.search(src)
    if m:
        raise ValueError(f"vwf asm: '{m.group(0).strip()}': no sp-relative byte/halfword access in Thumb-1 "
                         "(mov rN, sp first)")
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
    scode, s28, s30, smap, smenu, s2line, sgrid = strip_code(sfar, wt_off)
    write(sfar, scode, "vwf strip code")
    write(0x3A168, thunk(0x3A168, smap), "vwf strip thunk (map line 0x0803A168)")
    assert orig[0x3AEB2:0x3AEB6] == bl(0x0803AEB2, 0x0803A168), "vwf: grid call site moved"
    write(0x3A178, thunk(0x3A178, sgrid), "vwf gridline thunk (in the replaced map-line routine's body)")
    write(0x3AEB2, bl(0x0803AEB2, 0x0803A178), "vwf name-entry grid rows -> gridline")
    write(0x235D4, thunk(0x235D4, s28), "vwf strip thunk (intro scroll)")
    write(0x23E3C, thunk(0x23E3C, s30), "vwf strip thunk (credits)")
    write(0x14098, thunk(0x14098, smenu), "vwf strip thunk (OBJ menu cells 0x08014098)")
    write(0x110BAC, thunk(0x110BAC, smap), "vwf strip thunk (battle results 0x08110BAC, map-line twin)")
    write(0x110C88, thunk(0x110C88, s2line), "vwf strip thunk (battle text rows 0x08110C88)")
    for off, hx in TAG_ORIG.items():
        b = bytes.fromhex(hx)
        assert orig[off:off + len(b)] == b, f"vwf: unexpected bytes at {off:06X}"
    for ch, code in enfont.CODES.items():
        if ch != " ":
            write(small_glyph_offset(orig, code), ensmall.glyph(ch), f"small font {ch!r}")
    swt = ensmall.widths(NCODES)
    swt_off = img.alloc(len(swt))
    write(swt_off, swt, "vwf small widths")
    tfar = img.alloc(len(tag_code(0x800000, 0x800000)[0]) + 16)
    tcode, ttag, ttagw, tmap, tplate, tfill = tag_code(tfar, swt_off)
    write(0x01ED64, plate_patch(tplate), "vwf speaker plate (0x0801EC54 loop -> plate, centred by pixels)")
    plate_frame(orig, write)
    write(tfar, tcode, "vwf small-font code")
    write(0x110AE8, thunk(0x110AE8, tmap), "vwf smapline thunk (small-font BG labels 0x08110AE8)")
    # the default player name (40C51C) is copied to RAM 0x02010012 as 2 halfwords (2 JP chars): copy 5 (10 bytes,
    # "Riku" + NUL; the name field holds 5 characters, so the English default stays <= 4 letters)
    assert orig[0x3A85C:0x3A85E] == b"\x02\x22", "vwf: default-name copy moved"
    write(0x3A85C, b"\x05\x22", "default player name copy: 5 halfwords")
    assert orig[0x3A0A4:0x3A0B4] == bytes.fromhex("f0b557464e464546e0b481b000930004"), "vwf: 0x0803A0A4 moved"
    write(0x3A0A4, thunk(0x3A0A4, tmap), "vwf smapline thunk (name-entry small label 0x0803A0A4, twin of 0x08110AE8)")
    write(0x111B50, thunk(0x111B50, ttag), "vwf tag thunk (name tag 0x08111B50)")
    write(0x111B60, thunk(0x111B60, ttagw), "vwf tagw thunk (in the replaced routine's body)")
    write(0x10F98A, bl(0x0810F98A, 0x08111B60), "vwf tag centring: pixel width")
    write(0x111B70, thunk(0x111B70, tfill), "vwf fill7 thunk (in the replaced routine's body)")
    tag_tiles(orig, write, tfill)
    return far


def small_glyph_offset(rom, code):
    """ROM offset of the small font's (resource type 12) 32-byte glyph for Shift-JIS `code`, or None."""
    rt = 0x403DA4 + 12 * 8
    index, entries = (struct.unpack_from("<I", rom, rt + k)[0] & 0x1FFFFFF for k in (0, 4))
    i = code - 0x8140
    if not 0 <= i < SMALL_N:
        return None
    slot = struct.unpack_from("<h", rom, index + 8 + 2 * i)[0]
    if slot < 0:
        return None
    h8, h10 = struct.unpack_from("<HH", rom, entries + slot * 2 + 8)
    return (struct.unpack_from("<I", rom, 0x4028EC + 0x60)[0] & 0x1FFFFFF) + ((h8 & 0xFFF) << 16) + h10


if __name__ == "__main__":
    code, e1, e2 = far_code(0x800000, 0x801000)
    print(f"far code {len(code)} bytes, entry1 {e1:08X}, entry2 {e2:08X}")
    assert STATE == (0x81 << 18) - 0x100
