# Font and text drawing

- **Dialogue/menu font — verified** (rendered あいうえお漢字ＡＢＣ from it; draw path traced): 16×16 px, 4bpp,
  each glyph 128 bytes as 2×2 GBA tiles (TL, TR, BL, BR). Data at **0x1B4E74..0x2247F4** (3,571 glyphs,
  0x6F980 bytes = file-table entry 13 at 0x4028EC + 0x68).
- Lookup: resource type 13 via 0x080059A0. Index table 0x3E17CA (header `0d00 4017 1000 1000`: type 13,
  0x1740 codes, 16×16), then `int16 slot[code - 0x8140]` at +8 (-1 = no glyph), entry = 0x3E8C68 + slot×2
  (12 bytes; `((e[8] & 0xFFF) << 16) + e[10]` = byte offset into the glyph data).
- Drawn by 0x08002F68 → 0x08002F88 (code, buffer, x, 0x1C) from the text loop at 0x0801DF8C; glyphs go to a RAM
  buffer and reach VRAM by BIOS CpuSet (0x0B84/0x0B90), so no ROM read shows up on the VRAM write.
- Fixed advance 16 px; a 224 px line holds 14 characters. English needs a VWF (phase 5): an 8 px fullwidth-letter
  cell would still give only 28 characters per line.
- A small 8×8-ish symbol/kana font sits just before the big font (0x1B12D4..0x1B4E74, sweep sheet 283), probably for
  status numbers; confirm in phase 5.
