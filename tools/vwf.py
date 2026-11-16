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
    bne mram
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
@ flag != 0: a RAM string (native halfwords, e.g. the player name on the status page, was drawn "R i k u"):
@ copy <= 16 codes byte-swapped to the stack, then as above, then drop the outline (colour E: black in this OBJ's
@ palette, and the JP glyphs had none) from the plotted cells.
mram:
    push {{r4, r5, r6, lr}}
    sub sp, #36
    mov r4, sp
    movs r2, #0
mr_cp:
    ldrh r3, [r0, r2]
    cmp r3, #0
    beq mr_end
    lsrs r5, r3, #8
    lsls r3, r3, #24
    lsrs r3, r3, #16
    orrs r3, r5
    strh r3, [r4, r2]
    adds r2, #2
    cmp r2, #32
    blt mr_cp
mr_end:
    movs r3, #0
    strh r3, [r4, r2]
    adds r0, r4, #0
    lsls r1, r1, #22
    lsrs r1, r1, #17
    ldr r3, objvram
    adds r1, r1, r3
    adds r4, r1, #0
@ centred in its cells (the game centres the label by cell count: "Riku" sat 6 px left in the name plate)
    bl measure
    adds r3, r0, #0
    adds r3, #15
    lsrs r3, r3, #4
    lsls r3, r3, #4
    subs r3, r3, r0
    lsrs r3, r3, #1
    mov r0, sp
    movs r2, #0
    bl linex
    adds r0, #15
    lsrs r0, r0, #4
    adds r5, r0, #0
    lsls r2, r0, #6
mr_e:
    cmp r2, #0
    beq mr_done
    ldrh r0, [r4]
    movs r3, #0
mr_n:
    adds r1, r0, #0
    lsrs r1, r3
    movs r6, #15
    ands r1, r6
    cmp r1, #14
    bne mr_k
    lsls r6, r3
    bics r0, r6
mr_k:
    adds r3, #4
    cmp r3, #16
    blt mr_n
    strh r0, [r4]
    adds r4, #2
    subs r2, #1
    b mr_e
mr_done:
    adds r0, r5, #0
    add sp, #36
    pop {{r4, r5, r6}}
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
# Party-menu shikigami names (docs/re/font.md "OBJ cells size 8"): cards 0..2 at OBJ_NAME_TILE + 8k, card 4 (the
# lone centred card) at + 0x18. 0x3C0..0x3DF hold pixels only in battles (tools/debug/vramfree.lua over all 53
# scenes, work/qa/vfall), and battles reload their own OBJ tiles.
OBJ_NAME_TILE = 0x3C0
PNAME_THUNK, CTILE_THUNK, O8_THUNK = 0x08111B80, 0x08111B90, 0x08111BA0  # in the dead body of 0x08111B50

TAG_SRC = """
    b tag
    b tagw
    b smapline
    b plate
    b fill7
    b pname
    b ctile
    b o8
@ pname(r0 = str, r1 = tile offset from OBJ_NAME_TILE): a shikigami name on a party card, in the small font, into 8
@ tiles (64 px) at OBJ tile OBJ_NAME_TILE + r1 (the cards' own 5 tiles were too few once sprite cell 2 was widened to
@ 32x8 + 32x8 for the speaker plate; see obj8_patch).
pname:
    push {{lr}}
    ldr r2, pnbase
    adds r1, r1, r2
    lsls r1, r1, #5
    ldr r2, tobj
    adds r1, r1, r2
    movs r2, #8
    movs r3, #64
    bl splot
    pop {{r1}}
    bx r1

@ ctile(r6 = card k, r8 = 15k) -> OBJ_NAME_TILE + 8k - r8: replaces `movs r0, #0x1E0` before the card's sprite create
@ (the caller adds r8 back). Card 0 first clears all 32 name tiles (empty cards draw no name, and a battle may have
@ left pixels there).
ctile:
    push {{lr}}
    sub sp, #8
    cmp r6, #0
    bne ct_skip
    movs r0, #0
    str r0, [sp]
    mov r0, sp
    ldr r1, ctvram
    ldr r2, ctlen
    svc #0xb
ct_skip:
    lsls r0, r6, #3
    ldr r1, pnbase
    adds r0, r0, r1
    mov r1, r8
    subs r0, r0, r1
    add sp, #8
    pop {{r1}}
    bx r1

@ o8(r0 = str, r1 = tile index, r2 = size 8, r3 = cap tiles): a small-font OBJ label (0x08014098 size 8 callers,
@ their `movs r3, #0` patched to the cap) drawn at variable width into cap tiles at (index & 0x3FF), centred.
o8:
    push {{r4, r5, r6, lr}}
    adds r4, r0, #0
    lsls r1, r1, #22
    lsrs r1, r1, #17
    ldr r0, tobj
    adds r5, r1, r0
    lsls r6, r3, #3
    adds r0, r4, #0
    bl smeasure
    cmp r0, r6
    ble o8fit
    adds r0, r6, #0
o8fit:
    subs r0, r6, r0
    lsrs r0, r0, #1
    lsls r3, r0, #16
    orrs r3, r6
    lsrs r2, r6, #3
    adds r0, r4, #0
    adds r1, r5, #0
    bl splot
    pop {{r4, r5, r6}}
    pop {{r1}}
    bx r1

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

@ splot(r0 = str, r1 = dest tiles (8x8 4bpp, consecutive), r2 = tiles to clear, r3 = max px | start x << 16)
@ -> end x in px: plot the string in the small font (type 12) at variable width (small width table) from start x,
@ clipped to max px.
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
    lsrs r0, r3, #16
    mov sl, r0
    lsls r3, r3, #16
    lsrs r3, r3, #16
    mov fp, r3
    movs r0, #0
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
pnbase:  .word {nametile:#x}
ctvram:  .word {nametile_addr:#x}
ctlen:   .word 0x05000100
"""


def tag_code(far, swidths_addr):
    """Assemble the small-font blob at file offset `far`; returns (code, tag, tagw, smapline, plate entries)."""
    addr = 0x08000000 | far
    src = TAG_SRC.format(ncodes=NCODES, smalln=SMALL_N, swidths=0x08000000 | swidths_addr, tagpx=ensmall.TAG_PX,
                         tagtiles=TAG_TILES, platepx=PLATE_PX, platetiles=PLATE_TILES, nametile=OBJ_NAME_TILE,
                         nametile_addr=0x06010000 + OBJ_NAME_TILE * 32)
    return (_asm(src, addr), addr, addr + 2, addr + 4, addr + 6, addr + 8, addr + 10, addr + 12, addr + 14)


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


# The right-hand (enemy side, side 1) plate: raw 30-wide maps whose top row has the plate at cols 23..28. Widened
# leftwards to cols 21..28 (x 168..231, centre x 200 = the mirror of the left plate's x 40). The bottom border left of
# it (cols ..22) shifts left by 2, dropping two tiles of a flat run that starts at col FLAT.
PLATE_R_MAPS = {0x19E0BC: (11, 8, 13), 0x19E530: (10, 48, 49)}  # row start: (FLAT, bottom-left, bottom-right tile)
TAG_SIDE_STEP = 0x0810F9A4  # movs r2, #0xB0: tag x = 0x20 + side * 0xB0 + (10 - r) * 2 -> step 0xA0 (16 px left)


def plate_right(orig, write):
    """Widen the battle's right-hand speaker plate from 6 to 8 columns (leftwards) and centre the enemy-side name tag
    on it (docs/re/font.md "Enemy-side tag")."""
    hw = lambda *v: b"".join(struct.pack("<H", x) for x in v)
    for row, (flat, bl_, br_) in PLATE_R_MAPS.items():
        top = struct.unpack_from("<30H", orig, row)
        bot = struct.unpack_from("<30H", orig, row + 60)
        assert top[21:30] == (0, 0, 1, 2, 3, 4, 5, 6, 0), f"right plate map {row:06X} moved"
        assert bot[23:29] == (bl_, 9, 10, 11, 12, br_) and bot[flat] == bot[flat + 1] == bot[flat + 2], \
            f"right plate map {row:06X} bottom"
        write(row + 42, hw(1, 2, 3, 4, 5, 5, 5, 6), f"right plate map {row:06X}: top row cols 21..28")
        new_bot = bot[flat + 2:23] + (bl_, 9, 10, 11, 12, 12, 12, br_)
        write(row + 60 + flat * 2, hw(*new_bot), f"right plate map {row:06X}: bottom row, border shifted left 2")
    for i in (48, 49):
        o = PLATE_GFX + i * 32
        write(o, _plate_tile(orig[o:o + 32], PLATE_BANDS[1], 0), f"right plate bottom corner tile {i}: banded fill")
    s = TAG_SIDE_STEP & 0xFFFFFF
    assert orig[s:s + 2] == bytes.fromhex("b022"), "vwf: tag side step moved"
    write(s, bytes.fromhex("a022"), "battle name tag side 1: x step 0xB0 -> 0xA0 (centre x 200)")


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
    tcode, ttag, ttagw, tmap, tplate, tfill, tpname, tctile, to8 = tag_code(tfar, swt_off)
    write(0x01ED64, plate_patch(tplate), "vwf speaker plate (0x0801EC54 loop -> plate, centred by pixels)")
    plate_frame(orig, write)
    plate_right(orig, write)
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
    write(PNAME_THUNK & 0xFFFFFF, thunk(PNAME_THUNK & 0xFFFFFF, tpname), "vwf pname thunk (in the replaced routine's body)")
    write(CTILE_THUNK & 0xFFFFFF, thunk(CTILE_THUNK & 0xFFFFFF, tctile), "vwf ctile thunk (in the replaced routine's body)")
    write(O8_THUNK & 0xFFFFFF, thunk(O8_THUNK & 0xFFFFFF, to8), "vwf o8 thunk (in the replaced routine's body)")
    obj8_patch(orig, write)
    save_headers(orig, write)
    plate_names(orig, write)
    swap_list(img, write)
    num_patch(orig, write)
    join_patch(orig, write)
    return far


# Size-8 callers of 0x08014098 (docs/re/font.md "OBJ cells size 8"): (offset of `movs r3, #0`, offset of the bl,
# cap tiles, what). The label OBJs are fixed 8x8 cells, one per JP char of the longest string they show.
O8_CALLS = [(0x35214, 0x35216, 8, "shikigami page header 1292D8 (8 OBJs x 92..155)"),
            (0x35B24, 0x35B26, 5, "shikigami page labels table 0x08129328 (5 OBJs x 112..151)"),
            (0x30C7A, 0x30C7C, 4, "party Swap label 1292CC"),
            (0x33312, 0x33314, 7, "party Swap list names (vwf.swap_list: 8 tiles a row, 7 centred on the button)")]


def obj8_patch(orig, write):
    """Party-card names and the size-8 OBJ labels. Sprite cell 2 (also the dialogue speaker plate) is 32x8 + 32x8
    since plate_frame, so a card's name row shows 8 tiles from its base, but each card owned only 5 (0x1E0 + 15k;
    the HP digits follow), so "Kogenta" showed as "Kogen" + HP digits. Names move to 8 own tiles each."""
    bl_menu = 0x08014098
    # cards 0..2: sprite create (0x08030438: r8 = 15k; `movs r0, #0xF0; lsls r0, r0, #1` = 0x1E0, then add r8)
    assert orig[0x3043E:0x30442] == bytes.fromhex("f0204000"), "obj8: card sprite tile moved"
    write(0x3043E, bl(0x0803043E, CTILE_THUNK), "obj8 party card name sprite: tile 0x3C0 + 8k (ctile)")
    # cards 0..2: name draw (r5 = k): r1 = 8k, bl pname
    assert orig[0x343A2:0x343A4] == bytes.fromhex("211c"), "obj8: card name tile arg moved"
    assert orig[0x343A8:0x343AC] == bl(0x080343A8, bl_menu), "obj8: card name call moved"
    write(0x343A2, struct.pack("<H", 0x00E9), "obj8 party card name: r1 = 8k (lsls r1, r5, #3)")
    write(0x343A8, bl(0x080343A8, PNAME_THUNK), "obj8 party card name -> pname")
    # card 4 (tile literal 0x20D at 0x08030794 for the sprite, 0x080347C0 for the draw)
    for lit in (0x30794, 0x347C0):
        assert orig[lit:lit + 4] == struct.pack("<I", 0x20D), f"obj8: card 4 literal {lit:06X} moved"
    write(0x30794, struct.pack("<I", OBJ_NAME_TILE + 0x18), "obj8 card 4 name sprite tile 0x20D -> 0x3D8")
    write(0x347C0, struct.pack("<I", 0x18), "obj8 card 4 name: pname offset 0x18")
    assert orig[0x34672:0x34676] == bl(0x08034672, bl_menu), "obj8: card 4 name call moved"
    write(0x34672, bl(0x08034672, PNAME_THUNK), "obj8 card 4 name -> pname")
    for movs, call, cap, why in O8_CALLS:
        assert orig[movs:movs + 2] == bytes.fromhex("0023"), f"obj8: movs r3 at {movs:06X} moved"
        assert orig[call:call + 4] == bl(0x08000000 | call, bl_menu), f"obj8: call {call:06X} moved"
        write(movs, struct.pack("<H", 0x2300 | cap), f"obj8 {why}: cap {cap} tiles")
        write(call, bl(0x08000000 | call, O8_THUNK), f"obj8 {why} -> o8 (small VWF, centred)")


LIST_TILE_FN = 0x08111BB0                  # in the dead body of 0x08111B50, after the o8 thunk
LIST_HI_TILE = 0x3E0                       # rows 8, 9: free outside battles (vramfree.lua), above the card names


def swap_list(img, write):
    """Party Swap list (10 rows of owned shikigami at x 176, sprite create 0x08030AEC, names 0x08033314). Its rows
    use sprite cell 2, which plate_frame widened to 64 px (8 tiles), but each row owned only 5 OBJ tiles
    (0x21C + 5k), so a row showed 3 tiles of the next one ("GorozTak", work/qa/p8sw). A new cell id can't help:
    ids above 662 (bound literal 0x02960000, 6 sites) are another resource type. So each row gets 8 tiles of its
    own: rows 0..7 at 0x21C + 8k (to 0x25B; 0x262 is the scroll thumb), rows 8, 9 at 0x3E0 + 8(k-8). Names go
    through o8 capped at 7 tiles (56 px; "Tsuiga White" is 53) with the row moved 4 px left so the window is
    centred on the button (inner x 176..224); tile 7 stays blank over the scroll bar (x 228..236)."""
    orig = img.orig
    t = LIST_TILE_FN & 0xFFFFFF
    hi = LIST_HI_TILE - 64                 # 8k + hi for k >= 8
    lo = 0x21C
    code = _asm("cmp r0, #8; bge hirow; lsls r0, r0, #3;"
                + "".join(f"adds r0, #{v};" for v in _split(lo)) + "bx lr;"
                + "hirow: lsls r0, r0, #3;" + "".join(f"adds r0, #{v};" for v in _split(hi)) + "bx lr", LIST_TILE_FN)
    assert t + len(code) <= 0x111C08
    write(t, code, "swap list row tile: k < 8 -> 0x21C + 8k, else 0x3E0 + 8(k-8)")
    # sprite create (r6 = k; r0 = tile, r1 is reloaded at 0x08030AE6)
    assert orig[0x30AC6:0x30AD0] == bytes.fromhex("b0008019872189004018"), "swap list: sprite tile code moved"
    write(0x30AC6, b"\x30\x1c" + bl(0x08030AC8, LIST_TILE_FN) + b"\xc0\x46\xc0\x46",
          "swap list row sprite tile (adds r0, r6, #0; bl tile fn)")
    # x 196 -> 192 (OBJ x 172): the 7-tile name window 172..228 is centred on the button (x 176..224)
    assert orig[0x30AD6:0x30AD8] == b"\xc4\x20", "swap list: row x moved"
    write(0x30AD6, b"\xc0\x20", "swap list row x 196 -> 192")
    # name draw (r5 = k, result r6; r0 and r1 are reloaded at 0x080332D2/0x080332D8)
    assert orig[0x332C8:0x332D2] == bytes.fromhex("a8004019872189004618"), "swap list: name tile code moved"
    write(0x332C8, b"\x28\x1c" + bl(0x080332CA, LIST_TILE_FN) + b"\x06\x1c\xc0\x46",
          "swap list name tile (adds r0, r5, #0; bl tile fn; adds r6, r0, #0)")
    assert struct.unpack_from("<I", orig, 0x33368)[0] == 0x01000050  # only 0x080332DA loads it
    write(0x33368, struct.pack("<I", 0x01000080), "swap list row clear: 8 tiles (was 5)")


def _split(v):
    out = []
    while v > 0:
        out.append(min(v, 255))
        v -= out[-1]
    return out


def plate_names(orig, write):
    """Speaker plate, shikigami case (a0 != 0): the name came from the RAM copy 0x020027B0 + 16*i, which new game
    fills with only 5 characters of table 0x0812AEE0[i] (0x080111F4), so "Kogenta" showed as "Kogen". Read the
    table itself instead (the build repoints it to the English; `plate` treats a 0x08.. address as a ROM string):
    r6 = [0x0812AEE0 + 4*i] in place of r6 = 0x020027B0 + 16*i. The RAM copy has no other reader (text variables
    0x0080..0x00C7 occur in no script)."""
    assert orig[0x1ED5C:0x1ED64] == bytes.fromhex("464631010e480e18"), "vwf: plate name path moved"
    assert orig[0x1ED9C:0x1EDA0] == struct.pack("<I", 0x020027B0), "vwf: plate name literal moved"
    write(0x1ED5E, struct.pack("<H", 0x00B1), "vwf plate shikigami name: index*4")  # lsls r1, r6, #2
    write(0x1ED62, struct.pack("<H", 0x5846), "vwf plate shikigami name: ldr r6, [r0, r1]")
    write(0x1ED9C, struct.pack("<I", 0x0812AEE0), "vwf plate shikigami name: table 0x0812AEE0 (was RAM)")


# Save / Load screen headers (str_save 127968 記録, 127970 読込み): one 16x16 OBJ per JP char, spaced 36 px apart
# (x = base + i*9*4), so a VWF line running across the cells showed as "Loa   d". Step 16 px instead (x = base +
# i*4*4), re-centred on the same middle. (offset of `lsls r0, r7, #3; adds r0, r0, r7`, offset of `movs rX, #base*2`,
# its original halfword, new base*2)
# (x-step multiply, base `movs`, its original halfword, JP header centre x, string id, what). The new base x puts
# the English word's centre on the JP header's centre (Save: cells 92/128 -> 92..144 = 118; Load: cells 76/112/148
# -> 76..164 = 120); the old fixed bases (102 / 96) left both words left of centre.
HEADERS = [(0x130EE, 0x130F4, 0x23C8, 118, "127968", "Save header (2 cells)"),
           (0x13176, 0x1317C, 0x21A8, 120, "127970", "Load header (3 cells)")]


def save_headers(orig, write):
    import json
    entries = json.loads((Path(__file__).resolve().parent.parent / "script" / "str_save.json")
                         .read_text(encoding="utf-8"))["entries"]
    en = {e["id"]: e.get("en") or "" for e in entries}
    for mul, base, hw, centre, sid, why in HEADERS:
        assert orig[mul:mul + 4] == bytes.fromhex("f800c019"), f"vwf: header x step moved at {mul:06X}"
        assert struct.unpack_from("<H", orig, base)[0] == hw, f"vwf: header base moved at {base:06X}"
        x = centre - enfont.text_width(en[sid]) // 2
        new = 2 * (x + 8)     # the immediate is 2 * (x + 8): 0xD0 drew the first cell at x 96, 0xDC at 102
        assert 0 <= new <= 0xFF, f"vwf: {why} base x {x}"
        write(mul, bytes.fromhex("b800001c"), f"vwf {why}: x step 36 -> 16")  # lsls r0, r7, #2; adds r0, r0, #0
        write(base, struct.pack("<H", (hw & 0xFF00) | new), f"vwf {why}: base x {x}")


# Battle messages built as name + number + suffix (docs/re/font.md "Number at a fixed offset"): these callers of
# the number writer 0x0811B670(value, digits, dest) pass dest = buffer + the JP name's byte length, so a longer
# English name was cut ("Atta21down!", "Bo16 damage!"). Each bl goes to an entry that steps back to the buffer start
# and moves dest to the string's NUL. (bl offset, bytes back to the buffer start, what)
NUM_CALLS = [(0x0F8B56, 6, "stat up: dest = buf+8 (4-char stat) or buf+6 (妖力)"),
             (0x10098C, 6, "stat down (r8 base): buf+8"),
             (0x100D70, 6, "stat down (sb base): buf+8 or buf+6"),
             (0x10423E, 4, "Both sides + damage: buf+4"),
             (0x11F910, 0x22, "level up: buf+34")]
NUM_FN = 0x08110BBC  # in the dead body of 0x08110BAC, after its strip thunk
NUM_WRITER = 0x0811B670
NUM_SRC = """
back6:  subs r2, #6
        b scan
back4:  subs r2, #4
        b scan
back34: subs r2, #0x22
scan:   ldrb r3, [r2]
        cmp r3, #0
        beq go
        adds r2, #1
        b scan
go:     ldr r3, writer
        bx r3
        .align 2
writer: .word {writer:#x}
"""


def num_patch(orig, write):
    code = _asm(NUM_SRC.format(writer=NUM_WRITER | 1), NUM_FN)
    assert len(code) <= JOIN_FN - NUM_FN, "vwf: number fix overruns into the join routine"
    write(NUM_FN & 0xFFFFFF, code, "vwf number-at-NUL entries (dead body of 0x08110BAC)")
    entry = {6: NUM_FN, 4: NUM_FN + 4, 0x22: NUM_FN + 8}
    for off, back, why in NUM_CALLS:
        assert orig[off:off + 4] == bl(0x08000000 | off, NUM_WRITER), f"vwf: number call moved at {off:06X}"
        write(off, bl(0x08000000 | off, entry[back]), f"vwf number at NUL: {why}")


# Shikigami pages (docs/re/font.md "Joined OBJ strings"): the game draws kind, then 族 / の (+ name) as separate
# 0x08014098 calls, each starting at the next 16 px OBJ cell, so English showed "Silver  clan" / "Byakko-  Kogenta"
# (a 2..15 px gap plus the space). The first call of each group goes to `join`, which draws the strings as one
# line; the later calls become `movs r0, #0; nop`. Strings come through the same ROM literals the game uses (the
# build repoints them), the name through the shikigami name table, index r6 as at 0x08035C7A.
JOIN_FN = NUM_FN + 0x30
CLAN_LIT, NO_LIT, NAMES_LIT = 0x08036210, 0x08035C9C, 0x08035CA0  # literal words: 0812938C 族, 0812933C の, 0812AEE0
JOIN_CALLS = [(0x0361E4, (0x0361FC,), "clan", "page 1 kind + clan (Tsuiga)"),
              (0x036240, (0x036258,), "clan", "page 1 kind + clan"),
              (0x03628A, (0x0362A0,), "clan", "page 1 kind + clan, second slot (Tsuiga)"),
              (0x0362E0, (0x0362F6,), "clan", "page 1 kind + clan, second slot"),
              (0x035C60, (0x035C74, 0x035C8C), "head", "page header kind + - + name")]
JOIN_SRC = """
clan:   push {{r4, r5, r6, r7, lr}}
        ldr r5, clanlit
        ldr r5, [r5]
        movs r6, #0
        b join
head:   push {{r4, r5, r6, r7, lr}}
        lsls r7, r6, #2
        ldr r6, nameslit
        ldr r6, [r6]
        ldr r6, [r6, r7]
        ldr r5, nolit
        ldr r5, [r5]
join:   sub sp, #84
        add r4, sp, #4
        adds r2, r4, #0
        bl cpy
        adds r0, r5, #0
        bl cpy
        cmp r6, #0
        beq jend
        adds r0, r6, #0
        bl cpy
jend:   movs r3, #0
        strb r3, [r2]
        str r3, [sp]
        adds r0, r4, #0
        movs r2, #16
        bl {menu:#x}
        add sp, #84
        pop {{r4, r5, r6, r7}}
        pop {{r1}}
        bx r1
cpy:    ldrb r3, [r0]
        cmp r3, #0
        beq cpy_e
        strb r3, [r2]
        adds r0, #1
        adds r2, #1
        b cpy
cpy_e:  bx lr
        .align 2
clanlit:  .word {clan:#x}
nolit:    .word {no:#x}
nameslit: .word {names:#x}
"""


def join_patch(orig, write):
    src = JOIN_SRC.format(menu=0x08014098, clan=CLAN_LIT, no=NO_LIT, names=NAMES_LIT)
    code = _asm(src, JOIN_FN)
    assert JOIN_FN + len(code) <= 0x08110C88, "vwf: join routine overruns the dead body"
    write(JOIN_FN & 0xFFFFFF, code, "vwf join (shikigami page kind + clan / header in one line)")
    entry = {"clan": JOIN_FN, "head": JOIN_FN + 10}
    assert _asm(src, JOIN_FN)[10:12] == _asm("push {r4, r5, r6, r7, lr}", 0)  # `head` entry offset
    for lit, want in ((CLAN_LIT, 0x0812938C), (NO_LIT, 0x0812933C), (NAMES_LIT, 0x0812AEE0)):
        assert struct.unpack_from("<I", orig, lit & 0xFFFFFF)[0] == want, f"vwf: join literal moved at {lit:08X}"
    for first, later, kind, why in JOIN_CALLS:
        assert orig[first:first + 4] == bl(0x08000000 | first, 0x08014098), f"vwf: join call moved at {first:06X}"
        write(first, bl(0x08000000 | first, entry[kind]), f"vwf join: {why}")
        for off in later:
            assert orig[off:off + 4] == bl(0x08000000 | off, 0x08014098), f"vwf: join call moved at {off:06X}"
            write(off, b"\x00\x20\xc0\x46", f"vwf join: {why} (drawn by join)")


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
