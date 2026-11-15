# Font and text drawing

- **Dialogue/menu font — verified** (rendered あいうえお漢字ＡＢＣ from it; draw path traced): 16×16 px, 4bpp,
  each glyph 128 bytes as 2×2 GBA tiles (TL, TR, BL, BR). Data at **0x1B4E74..0x2247F4** (3,571 glyphs,
  0x6F980 bytes = file-table entry 13 at 0x4028EC + 0x68).
- Lookup: resource type 13 via 0x080059A0. Index table 0x3E17CA (header `0d00 4017 1000 1000`: type 13,
  0x1740 codes, 16×16), then `int16 slot[code - 0x8140]` at +8 (-1 = no glyph), entry = 0x3E8C68 + slot×2
  (12 bytes; `((e[8] & 0xFFF) << 16) + e[10]` = byte offset into the glyph data).
- Drawn by 0x08002F68 → 0x08002F88 (code, buffer, x, 0x1C) from the text loop at 0x0801DF8C; glyphs go to a RAM
  buffer and reach VRAM by BIOS CpuSet (0x0B84/0x0B90), so no ROM read shows up on the VRAM write.
- Fixed advance 16 px; a 224 px line holds 14 characters. English uses a VWF (below): ~40 characters per line.
- Glyph colours: F = body, E = 1 px outline, 0 = transparent (the plotter skips 0, so glyphs can overlap).
  Lookup detail: entry = 0x3E8C68 + slot×2 (`tools/font.py show ROM 82A0`).

## Dialogue draw path — verified (disassembly + marker build in-game, 2026-11-16)
- 0x08002F88(buf, code halfword as stored, idx, 0x1C, [sp]=0xE20/0x700) plots a glyph pixel by pixel at
  x = (idx % 14)·16 + 8, y = (idx / 14)·16 into the 4bpp buffer [0x0201DE48] (28 tiles per row).
- Callers: wrapper 0x08002F68 ← script text 0x0802DE96 (cursor **0x0201E7BC** += 1 per char) and variables
  0x0801E068 (`{00C8}`.. one char per call, ≤5 chars, sub-index 0x0201E71E); string drawer 0x080144F4 (BL at
  0x08014526: NUL-terminated padded strings, idx 0.., no newline code — wraps by idx/14).
- `{0000}` newline sets the cursor to 14 (0x0802DD36) — the box is 2 lines; `{0010}` page clears the buffer and the
  cursor (0x0802DBE8 / 0x0802DCC8). 0x0802A520 / 0x0802D3B2 only reset it.

## English: VWF — verified in-game (marker build, intro_event)
- `tools/enfont.py`: 93 narrow glyphs (own art, no licence issue) written over the fullwidth Shift-JIS codes
  (Ａ 0x8260..., digits 0x824F, punctuation; " and ' = ” ’), so English is plain Shift-JIS to every parser.
  `encode_en` turns `en` into `[XXXX]` tokens; "\n" = `{0000}` in scripts, code 0x81AD (no glyph) in string
  tables. Cap height 9, x-height 6, advance = art width + 1.
- `tools/vwf.py`: thunks at 0x08002F68 / 0x08002F78 (BL 0x08014526 retargeted) to vwf_pos in free space; pixel
  cursor in EWRAM **0x0203FF00** (last idx, next x, last buf, x, y); sequential idx continues at the cursor, any
  other idx starts at the game's own cell; width table 1 byte per code (JP = 16, so Japanese still lines up);
  auto-wrap past x 232; 0x81AD = newline; 0x08002FFE.. reads x/y from the state; `{0000}` now sets idx 64.
- Box: text x 8..232 (224 px). Marker line of 221 px shows whole; the exact last column is still to be measured.
- Other renderers seen in the marker build (still fixed 16 px cells, need their own work): the speaker name tag
  (showed `4050`), the intro scroll (vertical columns).

- A small 8×8-ish symbol/kana font sits just before the big font (0x1B12D4..0x1B4E74, sweep sheet 283), probably for
  status numbers; confirm in phase 5.
