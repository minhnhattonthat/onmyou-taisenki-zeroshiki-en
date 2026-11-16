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
- Box: text x 8..232 (224 px): a stress line exactly 224 px wide shows whole (work/qa/wg1/intro_event-z.png). The
  page-wait orb sits at x 226.. over row 2 (work/qa/tort/orb.png), so a page's last line gets 216 px.

## Width gate (2026-11-16): `tbl/windows.json`, `tools/windows.py`, `tools/lint.py`
- `tools/debug/drawcalls.lua` logs (routine, caller, string) for every renderer; `windows.py map TOUR` turns a tour
  into `drawmap.tsv` (entry id → renderer, scenes; ROM pointers mapped through the build's `.writes`).
- Stress lines: `windows.py fill PX [big|small] [head]` = a line exactly PX wide; `build.py --qa ID=...`.
- Measured: dialogue 224 (last line of a page 216), battle window 0x080029F0 **220** (row 1 shows 224, row 2 drops a
  glyph ending past x 228), map-menu area name: the padded drawer stops after **28 characters**, status labels =
  the JP's 16 px cells (the next label's OBJ tiles follow), battle tag 40 px small font.
- Glyph torture line (all 93 glyphs + double spaces) renders correctly in the dialogue and battle windows
  (work/qa/tort/z.png, ie2.png).
- Session 6 (2026-11-16): **battle_2row** 0x08110C88 = 224 px row 1 + **208 px row 2** (row 2's tiles follow row
  1's; 224 + 224 overran into the battle BG tiles, `row_px` in windows.json); **intro strip** 224 px from x 8;
  **credits** 240 px from x 0; **small labels** = the JP's tiles (all 10 callers of 0x08110AE8 read: dests 0x80
  apart for 40F718/24/30; 410C0C and 410C80 "もどる" (x 27) share 0x06009800).
- The dialogue **speaker plate** is its own routine **0x0801EC54**(a0, name index r8, a2) (one caller 0x0802C204):
  string = 0x0812802C if a2, else table 0x0841392C[index] (str_char_names) if index, else the player name RAM
  0x020025AE; a0 ≠ 0: 0x020027B0 + 16·index (RAM, shikigami names). RAM strings are native halfwords, ROM ones
  byte-order. Loop 0x0801ED64..0x0801EE28 put ≤ 5 small-font glyphs (type 12) in OBJ tiles 0x68..0x6C, then
  x += table 0x08128038 [n] = (0, 16, 12, 8, 4, 0) halfwords, i.e. (40 − 8n)/2. Now `vwf.plate_patch`: the loop
  calls `plate` (TAG_SRC; RAM strings copied byte-swapped, splot ≤ 40 px) and sets n = 1, table[1] = (40 − w)/2
  in the caller's stack copy: centred by pixels. Verified 40 px stress name (work/qa/sp2/final.png) and JP names
  from all three sources (work/qa/sp3/plates.png). `fontcalls.lua --var FONTTYPE=12` found it.
- **Speaker plate widened** (session 13, `vwf.plate_frame`): the plate's text OBJs come from sprite **cell 2** frame 0
  (cell table 0x08403DA4: id·8 → (index, frames); frame 0x3E798C = n 2, parts x −20 32x8 tile +0, x +12 8x8 tile
  +0x80 bytes; sprite x 32 → OBJ base **x 12**, not 16). Part 2 is now 32x8 (tiles 0x68..0x6F; 0x6D..0x6F were
  blank in every toured scene). The BG frame is BG0 (cbb 1, map sbb 0) drawn by the generic layer copier 0x08006EE8
  (src − base | pal) from **raw 30-wide maps** in ROM: plate at 0x19DE66 and 0x19E1EA (top row col 1..6 = tiles
  1..6, bottom row +60 bytes = 8..0xD, then the box border's decoration 0xE.. and plain border); 0x19E0EA is a
  right-hand plate variant, left alone (the plate routine always puts the OBJs left). Tiles are raw at 0x171E6C
  (resource entry 0x1B0E94). The original fill was a diagonal gradient (palette 6..0xC), so repeating a tile showed
  a seam: the fill is now one colour per pixel row (bands 6,7,7,8,8 / 9,9,A,A,B), the middle tiles are identical,
  and the maps use 1,2,3,4,5,5,5,6 / 8,9,A,B,C,C,C,D (8 columns, interior x 10..69). Text centred on x 40:
  table[1] = (56 − w)/2, cap 56 px. Shots work/qa/plw/z.png, work/qa/plt/plates.png. Probes: `bgdump.lua`
  (BG maps + VRAM/palette dump once an OBJ tile shows), `valwatch.lua` (every write of a value to an address).
- **names_list** (skills, weapons, techniques) is drawn by the OBJ-cell renderer 0x08014098 (VWF) from the
  shikigami menu's page routine **0x08035CA4**(id r0 ≤ 0x4B, page r1 0..4, r2), callers 0x08034EA4/0x08034EDC/
  0x080354C4/0x080354FE/0x080355D2/0x08035606. The page is u16 **0x0200512C**; d-pad **left** steps it back and
  wraps (0 → 4 → 3 → 2 → 1; handler 0x0803551C: keys & 0x30), right only moves the bottom selector, R/L do nothing.
  Scenes `menu_shiki_p1..p4`. OBJ tiles per page (`tools/debug/objcalls.lua` on the original ROM, work/qa/oc5):
  page 1 (affinity) labels 0x20/0x58/0x74/0x100/0x11C, kinds 0x6C/0x114; page 2 (ability + weapon) label 0x20,
  **ability description 0x58 = 28 cells as 2 rows of 14** (str_abilities, pad 14), label 0xC8, **weapon 0x104**
  (x 24), **skill 0x144** (x 56); page 3 (techniques) labels 0x20/0x58/0x90/0xC8/0x100/0x138 and **technique
  names 0x38/0x70/0xA8/0xE0** (8 cells each, x 105); page 4 = the same labels + button-input graphics.
  Measured (work/qa/nl2, nl3a/b): weapon 208 px, skill 176 px, technique 128 px, ability rows 224 + 224 with `\n`
  (the shared `line` plotter now moves x to the next multiple of 224 at code 0x81AD; a row exactly 224 px wide
  doesn't skip a row). Variants `weapon_name`, `skill_name`, `technique_name`, `ability_rows`.
- Other readers of those tables: 0x0810638E/0x08106402 build a battle message in RAM 0x0201A5C4 = weapon +
  (28 − its bytes)/2 × str 40E32C + str **40E534** + skill (0x0811B7AC = strcat, 0x0811B788 = byte count): the JP
  pads row 1 to 14 chars, so English 40E534 must start with `\n` (note on the entry). 0x08112642 builds
  `【` + ability name (table 0x0813B0EC) + `】` (40F9F0/40F9F4).
- **Battle super-move cut-in**: 0x081096EA reads techniques_b (table 0x0813BD78) and 0x08109614 matches each
  2-byte char of the name against the 380-entry table 0x0840E56C of one-kanji strings (**str_battle_kanji**, 257
  strings, only reader) to get a graphic index per kanji. So str_battle_kanji is data (variant `data_keys`,
  keep_jp), and `build.py` JP_COPIES gives that reader its own copy of the JP table + strings (literal
  0x0810971C), while the shikigami page (literal 0x08036548) reads the translated table
  (tests/test_build.py::test_cutin_keeps_japanese_keys).

## Name entry (2026-11-16)
- Renderers (`tools/debug/mapcalls.lua`, original ROM): title 40C524 = 0x0803A168 (lr 0x0803AD6F) at tiles
  0x06008020, 4 cells; label けってい 40C530 = **0x0803A0A4** (lr 0x0803AD89), a twin of the small-font label routine
  0x08110AE8, tiles 0x06008220 (right after the title's 4 cells: title budget 64 px); name field = RAM 0x02010012
  (lr 0x0803AE29) at 0x06008680, 5 cells up to the grid's tiles 0x06008900; grid rows = BL at **0x0803AEB2**
  (row strings from table 0x0840C1D4, 5 chars, x 17); prompts 40C540/40C560 = window routine.
- Patches (`vwf.py`): 0x0803A0A4 → `smapline`; the grid's BL → thunk at 0x0803A178 (dead body of the replaced
  0x0803A168) → `gridline`: one glyph centred per 16 px cell, every cell redrawn (plain VWF packed "ABCDE" into
  two cells and left the previous tab's kana in the rest, work/qa/ne1/abc.png). The default name 40C51C is copied
  to RAM by 0x0812414C(src, 0x02010012, **2** halfwords) at 0x0803A85C: now 5 (English "Riku" showed as "Ri").
- The name cursor is still placed at 16 px × name length (0x0803ADA4 and the typing code): cosmetic gap after a
  VWF name. Scene `name_entry_abc` = the ABC tab, `name_back` = B on the empty name.
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
**Tag budget: 40 px of `ensmall` width.**
**0x08110AE8** (BG labels, 10 callers) → `smapline`: n = ceil(small width / 8) tiles at dest, plotted by the shared
`splot`, map entries for those n tiles, returns dest + 32n. The original wrote one tile per char with no limit, so
a long string overwrote the BG tiles after dest (the marker build showed "hchc…" and "quick" fragments around the
battle wheel). Its budget per label = the JP's tile count × 8 px until measured (the tiles after dest belong to the
next label). Verified: `build.py --qa 410C0C="View foe"` in battle_forest draws clean (`work/qa/tag3/z.png`); the
marker build still overruns there because its markers fill 16 px per JP char (needs the small-font budget). The window glyph routine 0x080029F0 is NOT the tag (probes
`winopen.lua` / `wincalls.lua` see only battle messages and the name-entry question there).
Battle wins are RNG-dependent on the marker build (text timing changes the RNG): battle_win lost once and the game
returned to the title (not a crash).
The strip/map renderers write VRAM directly: plot by halfword read-modify-write (a byte store lands in both bytes).

- A small 8×8-ish symbol/kana font sits just before the big font (0x1B12D4..0x1B4E74, sweep sheet 283), probably for
  status numbers; confirm in phase 5.
