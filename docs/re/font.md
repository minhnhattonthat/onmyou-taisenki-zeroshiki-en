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
- Other renderers seen in the marker build (still fixed 16 px cells, need their own work): see "Renderer
  catalogue" below.

## Renderer catalogue — marker tour 2026-11-16 (`tools/debug/glyphreads.lua`: who reads font data, per scene)
Only three code paths read the 16×16 font:
1. **Dialogue** 0x08002F88 (reader pcs 0x08003058..0x08003344): script text, NPC talk, shikigami talk. VWF done.
2. **Window glyph routine 0x080029F0**(r0 = flag, r1 = window struct) — verified by disassembly: draws ONE glyph,
   code = halfword at `[[r1+0x20]]`-indexed string (byte-swapped), at **pixel** x = `[r1+4]`, y = `[r1+6]`
   (0x08002A08 / 0x08002A0C) into the 4bpp bitmap 0x02004244 (row stride `[r1+0xE]`·64), then copies it to VRAM
   `[r1+0x18]` (0x380 or 0x2D0 words via 0x08124148). Returns 0 at NUL, -1 for codes ≤ 0x813F, 1 after a glyph.
   Every fixed-cell text in the tour comes from here: menus/status labels, speaker name tags, area name, battle
   messages, intro scroll, name-entry prompts (pcs 0x08002B0A/0C0A/0D0E/0E0E). Only 4 BL callers: 0x08003500,
   0x080035CE, 0x080036D4, 0x08003796 (text-window system, struct 0x02005048 = EWRAM base 0x02000000 + 0x5048).
   Caller 0x08003558..0x080035F4 lays out by character count n = `[[0x02005068]]`: x = (n % 14)·16 + base x
   (0x0200505A), y = base y + 16·(n / 14) for 3 rows — the same cell grid as the old dialogue.
   **VWF plan:** a trampoline at 0x080029F0 that, like `vwf_pos`, keeps a pixel cursor per window struct: if n is
   the previous n + 1 for the same struct, draw at the cursor (x) and the current line's y, else adopt the game's
   x/y (line start); advance by the width table; code 0x81AD = newline (y += 16, x = line start x). The game's
   own row change at n = 14/28 must be ignored for sequential calls. Callers 0x080036D4 / 0x08003796 still to
   read (same formula expected). Line breaks then come from the build (explicit 0x81AD), widths from the lint.
3. **Staff credits**: no plotter reads at all, only BIOS CpuSet (pc 0x00000B8E) copying font data straight to the
   tile area — the credits copy whole glyph tiles by code; English needs a narrow-tile or pre-rendered approach.

### Full renderer list — `tools/debug/fontcalls.lua` (every caller of the glyph lookup 0x080059A0 with type 13), 44 scenes, 2026-11-16
| caller (lr) | routine | draws | English status |
|---|---|---|---|
| 0x08002FDF | dialogue 0x08002F88 | script text, NPC/shikigami talk, `pad` strings | VWF (`vwf.py` FAR_SRC) |
| 0x08002AC1 | window glyph 0x080029F0 | battle messages (and any window text) | VWF (`WIN_SRC`): per-call pixel cursor, verified battle_forest |
| 0x08023621 | strip 0x080235D4(str), 28 cells → [0x0201DE48] (VRAM) | intro scroll | VWF (`STRIP_SRC` strip28), verified |
| 0x08023E9F | strip 0x08023E3C(str), 30 cells | staff credits | VWF (strip30), verified; only ~240 px of a line shows |
| 0x0803A1B9 | map line 0x0803A168(x, y, pal, map, [sp] dest, base, str) | name-entry title, name field, kana grid | VWF (mapline: tiles + 2×2 map entries for ceil(w/16) cells), verified |
| 0x0801417B | OBJ cells 0x08014098(str, tile index, size 16/8, flag, max): one 16×16 glyph per char into OBJ tiles 0x06010000 + ((index + 4n) & 0x3FF)·32 (1D), ≤ 28 chars; size 8 = small font type 12, 1 tile/char | status / save / shikigami menu labels (~110 callers) | VWF (`STRIP_SRC` menu: size 16 + flag 0 → line plotter over ceil(w/16) cells, returns that count; size 8 / flag ≠ 0 run the original), verified menu_status, menu_shikigami |
| 0x080142EB | number drawer 0x08014220 (digits) | status numbers | kept: fullwidth digit codes, one per cell |
| 0x08110BF3 | 0x08110BAC(x, y, pal, map, dest, base, str): twin of the map-line renderer | battle text box (tutorial and every battle message box with 2 rows) | VWF (thunk to `mapline`) |
| — | caller 0x08110C88 (same args): ≤ 28 bytes → one row, else 28 bytes + rest copied into a 60-byte stack buffer → 2 rows | | replaced (`twoline`): row = up to newline code 0x81AD or 224 px, bounded buffer, row 2 continues, rest dropped. A long English row overran the original's stack buffer and garbled VRAM. Verified tutorial_battle, battle_forest |
Fixed-cell texts not in this list: status digits (number drawer, above), and the small font (below).

### Small font (resource type 12) and the battle name tag
Lookup 0x080059A0(12, sjis + 0x7EC0): the resource table 0x08403DA4 (type·8 = index ptr, entries ptr) gives index
0x3E12FA (0x260 codes, 0x8140..0x839F) and entries 0x3E7ABC; glyph = 32 bytes (one 8x8 4bpp tile, body F, drop
shadow E right/below) at `[0x084028EC + 0x60]` + entry offset. `vwf.small_glyph_offset`. Users (`tagfind`-style
probe of every lookup in battle_forest): 0x08110AE8 (BG labels, one tile per char at map column x + i, e.g. the
hidden "テキをみる" at x 0, y 13 in battle; `linecalls.lua`), 0x08111B50 (name tag), and 0x08014098 size 8.
**Battle speaker name tag**: 0x0810F984 calls 0x08111B50(tile 0x3DB, str), which writes ≤ 5 glyphs into OBJ tiles
0x3DB..0x3DF (shown as OBJ 32x8 + 8x8, `tools/debug/oamfind.lua`; tiles 0x3E0+ belong to the next sprite), then
0x0811B788(str) = byte count n and the tag's x offset = (10 − n)·2 (stored at 0x02013740 with 0x20 + side·0xB0):
centred by bytes, 8 px a char. Patch (`vwf.py` TAG_SRC, small art `tools/ensmall.py`): 0x08111B50 → `tag`
(VWF in the small font, clipped to 40 px), 0x0810F98A bl → `tagw` at 0x08111B60 (the dead routine body):
(pixel width capped at 40, + 2) / 4, so (10 − r)·2 centres by pixels (Japanese: 8 px a char gives the byte count
back). Verified battle_forest "Kogenta", tutorial_battle "Ryuuko" (`build.py --qa`, `work/qa/tag2/z.png`).
**Tag budget: 40 px of `ensmall` width.** The window glyph routine 0x080029F0 is NOT the tag (probes
`winopen.lua` / `wincalls.lua` see only battle messages and the name-entry question there).
Battle wins are RNG-dependent on the marker build (text timing changes the RNG): battle_win lost once and the game
returned to the title (not a crash).
The strip/map renderers write VRAM directly: plot by halfword read-modify-write (a byte store lands in both bytes).

- A small 8×8-ish symbol/kana font sits just before the big font (0x1B12D4..0x1B4E74, sweep sheet 283), probably for
  status numbers; confirm in phase 5.
