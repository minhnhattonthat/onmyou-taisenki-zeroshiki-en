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
  Empty table entries hold 0x0200A000 (EWRAM) or the bare `/999` at 0x41FE5C; the 700..999 table has holes of
  0x0200A000 between used ids (711..736, 742, 760.., 780.., 800, 820.., 840.., 880..), so `tools/script_index.py`
  skips them rather than stopping (it stopped at 705 until session 25 and missed 78 scripts). A bare `/999` at 0x41F840 has no
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
**Quote picker** 0x08104E70: table r5 (0..9, the 10 battle-quote tables above, literals 0x08104EDC..0x08104F34),
entry r3 + 2*r4, string pointer in r0 at 0x08104F3A (r5 > 9 → 0). `tools/debug/quotecycle.lua` hooks it for text
coverage. The tech-quote tables 0x408258.. are reached through a per-shikigami table at 0x40A620 (85 u32: mostly
0x08408B74), whose reader is not found yet (no literal load). Session 24: indexed by shikigami id (entry 15 =
Kogenta → 0x409C20, 14 → 0x4093B0, 1 → 0x408258, 73 → 0x40A518, the rest → the default 0x408B74); each sub-table
holds ~84 string pointers. A read watch over 0x08408258..0x0840A76F saw **no** read in battle_win, the tutorial
battle, the battle wheel + L seal panel, or a battle with every unlock bit set (work/qa/tqw, work/qa/tq). The lines
describe technique effects ("Weapon summon!", "Shift the field to raise our Attack"), so they likely belong to a
technique/seal menu not reached yet. The only code literals near it are 0x0840A748 and 0x0840A844 (u16 pair tables
next to the map menu's area lookup 0x080163E6: area = u16 [r8 + 4 * [r7]]; which table is r8 is unchecked), not
the quote tables. Session 25: the per-shikigami table is 74 words (0x40A620..0x40A747; 0x40A748 starts the map
menu's u16 pairs). No ROM word points at 0x0840A620 (aligned or unaligned), no code literal lies in
0x08408000..0x0840A800 except 0x0840A748, and none of the 1,823 LZ77 blocks (work/lz) holds one: the tables are
dead data. All 258 tech quotes are waived in docs/text_unshown.tsv for that reason.
**Battle messages** (str_battle_msgs): each code site stores its string at [0x02010000 + 0x9BE0 + 4*idx] (idx =
s16 0x02019AA0; + 0x9BE8 = a name to put in front). The drawer 0x08102E76 loads it at 0x08102E88 and calls
0x0810F928 (with name) or 0x0810F9E0 (plain, r2 = message), then clears the field. `tools/debug/msgcycle.lua`
substitutes each unseen message there (r3 at 0x08102E8A, r0 = 0 at 0x08102E96), runner `msgjobs.py`.
**Scripts without a StartScript id:** Kogenta's L-button talk (pinned 0x6918F4) branches on story flags to ~50
hint lines; the tutorial-battle scripts hang off table 0x693080. `tools/debug/talkjobs.py` writes build/talk.gba (id
slots 705..710 pointed at their slots, nothing else changed) and jumps to each label.
**Area names** (str_areas): the map menu draws the current area's name once per opening, `bl 0x080144F4` at
0x080163F6 with r0 = word [0x0840B334 + 4 * area]; `tools/debug/areacycle.lua` substitutes each name there.

**Not text:** 0x128F50..0x128F64 is a u16 LE table of fullwidth digit codes ０..９ (number drawing) that scans as text.
Code literal-pool pointers are plain u32 words: repoint them by exact location, never by a ROM-wide value match.

## Extracted text (phase 4) — verified (tests/test_text.py)
- `script/*.json` from `tools/textdb.py dump`: 5,185 entries = 2,191 script text runs (20 `ev_<16 KiB block>` files
  + `tutorial`) and 2,994 table strings (36 `str_<group>` files, groups in `textdb.GROUPS`), ~100k JP characters.
  Format and fields: the textdb docstring. `build.py` reads it (`textdb.overrides`); `en` = `jp` everywhere
  rebuilds the original ROM (test).
- **Every script text run is dialogue**: the speaker/portrait is in the preceding op's args (`/098`, `/036`,
  `/124`...), never in the text. Control codes in the text: only `0010` (3,890), `0000` (2,539), `00C8` player
  name (149), `00CB`/`00CC` win/loss counts (5 each). No run is codes-only.
- **Coverage** (`textdb.py coverage`, test): 148 strtab scan candidates in the string areas have no pointer; all
  are 1-10 byte fragments of code/graphics (no 2+ kana). Outside the text areas, 4 text-like runs are data
  (`textdb.DATA_RUNS`: u16 LE glyph-code tables at 0x4E1DC9 / 0x4E5C0F, music bytes at 0x6EE2DB).
- **Gaiji — verified (rendered from the font):** the font holds kanji outside JIS level 1 at the Cyrillic codes
  0x8440..0x8459 (and Ⅴ at 0x8758): 0x8440 隕, 41 銛, 42 曼, 43 祓, 44 撼, 45 鉈, 46 鯔, 47 咬, 48 毬, 49 棍,
  4A 穹(?), 4B 棘, 4C 龕, 4D 礫, 4E 翔, 4F 跋, 50 扈, 51 巫, 52 澤, 53 條, 54 晏, 55 麒, 56 荼; 0x8457 = ラ・,
  0x8458 + 0x8459 = 衛・二 drawn across two cells. The dump adds `notes: gaiji Р=巫` to each entry that uses one.
- Left for the marker build: strings reached by base + immediate or built from code (none found yet), the tiny
  script at 0x129560. The one-kanji strings at 0x40EB5C.. (`str_battle_kanji`) are lookup keys for the battle
  super-move cut-in (docs/re/font.md "names_list"), not text. Code-built strings found so far: the weapon/skill
  battle message (0x0810638E) and `【ability】` (0x08112642).
