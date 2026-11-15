# Text engine, script format, pointers

Dump: `rom.sha1` (AGB-BITJ, 8 MiB). All offsets are file offsets; GBA address = 0x08000000 | offset.

## Encoding — verified
- **Shift-JIS**, 2 bytes per character, no custom table. Verified: decoded strings read as sentences
  (`tools/sjis_survey.py`), and the draw path tests `(c - 0x8140) <= 0x173F` (0x0802DB58, 0x08002FB6).
- **Only JIS level 1 is drawable**: codes 0x8140..0x987F. Anything outside that range in a text run is parsed as a
  4-character hex control code instead (0x0802A334, hex digits 0-9/A-F/a-f, weights from 0x08129124).
- **No single-byte (ASCII) characters.** An ASCII byte in a text run starts a 4-char control code. English needs
  either fullwidth Shift-JIS letters (0x8260..0x829A, 16 px wide each) or an engine change (phase 5).

## Event script format — verified (decoded known strings; interpreter traced at 0x0802A5C8 / 0x0802DB50)
Plain ASCII bytecode with inline Shift-JIS text, in **0x41FE58..0x46B000** (~300 KB).
- **Opcode** = `/` + 3 digits (`/091`), decoded as nibbles (0x0802A5D0). Fixed-length ASCII argument string follows
  (digits, A-F, `-` for negatives). `/999` stops execution; the script's bytes end at a NUL (see below).
- After an opcode's arguments, if the next byte is not `/`, the stream is **text** until the next `/`: Shift-JIS
  characters and 4-char hex codes:
  - `0000` newline, `0010` wait for key + new page (last one before `/091` closes the box),
  - `00C8` player name (RAM 0x020025AE table), `00C9`/`00CA`/`00CB`/`00CC` other variables (0x0801DF8C;
    `00CB`/`00CC` = win/loss counts in the training script), 0x0080..0x00C7 = variables via 0x020027B0.
- Text after `/073xxxx` = dialogue; after `/098xxxxxxxx`, `/079..`, `/036..`, `/124xxxx`, `/048..`, `/054..` =
  speaker/portrait set-ups followed by dialogue; `/042`/`/037`/`/026` = yes/no and plain prompts.
- **Jumps are by label number** (`/124NNNN` = label, `/123...` = conditional jump with label args), not byte
  offsets: text can grow freely inside a script. Guess, from arg shapes; confirm in phase 3/4 by relocating one script.
- Argument lengths (chars after the 3-digit opcode), from every occurrence followed by `/`:
  0 for 022 026 037 042 045 046 058 059 060 065 072 077 078 080 081 082 085 086 091 106 142 143 224 225 226 230 231
  233 236 240 999; 4 for 017 034 047 053 073 074 084 095 099 119 122 124 128 130 140 222 227 228 232 239;
  8 for 012 014 036 048 054 079 094 098 121 125; 12 for 015 018 029 083 087 144 229; 16 for 013 035 070 135 141;
  20 for 123; 28 for 129; 40 for 052; 52 for 116. Opcodes seen only once or twice (070, 087, 129, 135 with `-`)
  need the extractor's roundtrip test to confirm.
- Stats: 2,373 text runs, ~63k characters. **Line width: 14 full-width chars (224 px)**; 99.9% of lines are ≤14.

## Script regions and the identity build — verified (phase 3: `tools/evscript.py`, `build.py`, tests/test_build.py)
- **A script ends at a NUL byte, not at `/999`**: `/999` and `/235` (0 args) also appear mid-script after branches.
  After the NUL the game pads with NULs to a 4-byte boundary (end%4==0 → 4 NULs, ==2 → 2).
- **Corrected arg table** (every opcode followed by `/` or NUL, one length each; test checks it): adds 024 235 (0),
  133 (4), 093 136 (8), 117 134 (12), 055 (32) — the map-script opcodes the recon table lacked. Code: `evscript.ARGS`.
- **Regions** (walk cleanly as pointer runs / scripts / NUL pad, nothing else): main **0x419300..0x46A104** (map
  scripts from 0x419304, the id tables 0x41A058 / 0x41F2D8 / 0x41F848 / 0x41FE64..0x420CEC sit inside it, event
  scripts to 0x46A104; data follows) and tutorial **0x6918E8..0x693978** (code → 0x6918E8 → slot 0x6918F0 →
  script; table 0x693080 points straight at scripts). 541 scripts, 2,191 text runs, ~64.5k characters.
- **Slots:** every script but the tutorial ones has a u32 right before it pointing at it; tables point at slots
  (two slots, 0x4267D8 / 0x446C54, point at another script). The only pointers to script starts are those slot /
  tutorial-table words (722 in all), so a script moves by rewriting its slot(s); tables never move.
  Empty table entries hold 0x0200A000 (EWRAM) or the bare `/999` at 0x41FE5C. A bare `/999` at 0x41F840 has no
  pointer (dead). A tiny no-text script sits in the string area at 0x129560 (slot 0x12955C); left alone.
- **Pinned script:** 0x6918F4 must sit right after its slot 0x6918F0: code 0x0801DC90 loads [0x6918E8] (= the
  slot) and scans forward to the first `/`, while 0x08027FB8 dereferences the same word twice. `evscript.PINNED`;
  the build moves it together with a fresh slot and points 0x6918E8 at that slot.
- **Relocation proven:** `build.py --relocate-all` moves all 541 scripts and 2,994 strings past 8 MiB (ROM 9 MiB,
  old rooms 0xFF-filled); every warp scene still runs, and `tools/debug/romreads.lua` + `stale_reads.py` show no
  read of a vacated room except one the original makes too (below). Jumps are by label, not byte offset.
  The first run caught two misses, both fixed: the pinned script above, and 0x40F73C (code 0x0810E1A2), an empty
  string made of the NULs after "　カット" at 0x40F730 (a string's room now stops at any pointed-at byte).
- **Shikigami name variables are 5 characters:** at boot 0x080111F4.. copies 5 halfwords of each of the 80 names in
  table 0x12AEE0 into RAM 0x020027B0 + i*16 (the RAM behind the 0x0080..0x00C7 text variables), skipping non-Shift-JIS values and
  not stopping at NUL (entry 79, the empty 0x12B020, runs on into 0x12B024). English names longer than 5 cells
  need that copy (and its readers) widened in phase 5.

## Script pointers — verified (table bytes)
- Main table **0x420000..0x420CEC**: 827 u32 pointers into 0x41FE58..0x46A040 (275 unique; unused slots →
  0x0841FE58 = an empty `/999` script). Read by 0x0802A402.
- Further script pointers: one u32 right before many scripts (e.g. 0x421224 → 0x421228) — a second index; and tables
  in 0x400000..0x41FFFF (e.g. 0x41F000 region scripts). The extractor must collect every u32 that points at a script
  start, ROM-wide, and rewrite them all.
- Tutorial scripts **0x6930A4..0x693908** (same format), pointer table 0x693080 (5 entries) and 0x688F04/0x688F78.

## String tables (NUL-terminated Shift-JIS, outside the scripts) — verified (tools/recon_strings.py)
Every string below is reached by an aligned u32 pointer. Fixed-width multi-line strings pad each line with
full-width spaces (`　`) to 14 chars instead of using a newline code.
| Range | Contents | Pointer tables |
|---|---|---|
| 0x125E04..0x12634C | battle command help (`【攻撃】…`), name-entry kana grid | 0x125DB0 (21), 0x125E68 (13), 0x126170 (8) |
| 0x127968..0x1279F8 | save/load messages | code literal pools 0x013164.. |
| 0x12802C..0x128CD8 | intro scroll text, **staff credits** (`ゲームソフト制作`…) | 0x12836C (21), 0x128CF8 (107) |
| 0x128F50..0x129404 | system messages, status labels, items | code literals 0x024478..0x036810, 0x129180, 0x129294, 0x129328 |
| 0x12B024..0x12BB48 | shikigami names, elements, skill names, weapons | 0x12AEE0 (79), 0x12B3AC (31), 0x12B4F8 (73), 0x12B910 (72) |
| 0x12B644..0x13AB74 | battle quotes: 10 tables × 158 entries | 0x12BB50, 0x12D00C, 0x12EA60, 0x130040, 0x131BD0, 0x13355C, 0x134B10, 0x1361D4, 0x137620, 0x138FF4 |
| 0x13AC10..0x13C21C | special abilities, technique names | 0x13AB90 (32), 0x13B0EC (319), 0x13BD78 (76) |
| 0x4083A8..0x40A600 | more battle quotes | 0x408258, 0x408B74, 0x4093B0, 0x409C20 (84 each), 0x40A518 (20) |
| 0x40B6B4..0x40BEA0 | area/location names | 0x40B334 (224) |
| 0x40C2A0..0x40C930 | name-entry kana, link-cable/menu messages | 0x40C1D4 (51), code literals 0x03A3C8..0x040978 |
| 0x40C9BC..0x40EF5C | battle messages (`のダメージ！`…) | code literals 0x050BA4.., 0x0F8B80, 0x1009B4, 0x100D9C, 0x40E56C (380) |
| 0x410AE4..0x410BD0 | battle tutorial help | 0x410AD0 (5) |
| 0x413BFC..0x4140F8 | character names | 0x41392C (144) |
Full list with every pointer location: `python -X utf8 tools/recon_strings.py ROM OUT.tsv` (544 pointer clusters).
The build's model is `tools/strtab.py`: strings in 0x120000..0x140000 and 0x400000..0x419300 that an aligned u32
from code (0..0x120000) or those areas reaches: 2,994 strings, 3,899 pointer words, none pointed at mid-string.
**Not text:** 0x128F50..0x128F64 is a u16 LE table of fullwidth digit codes ０..９ (number drawing) that scans as text.
Code literal-pool pointers are plain u32 words: repoint them by exact location, never by a ROM-wide value match.
