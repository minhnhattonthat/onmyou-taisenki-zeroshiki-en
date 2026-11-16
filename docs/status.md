# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 8. QA in the emulator in progress (session 23: Drive screen fixed, full tour10 with the text probe,
  manifest re-made, vqa run; text coverage 2342/5185 shown + 97 waived). Last build 2026-11-16 (session 23):
  build/onmyou_zeroshiki_en.gba = 606f89ee… (tour10 `work/qa/cover/tour10` ran on it; manifest
  work/qa/manifest.tsv records it).
- **Done:**
  - Step 0: ROM pinned (`rom.sha1`), MesenCE 2.2.1 + GBA BIOS in `tools/mesen/`, guard hook in `.claude/settings.json`
    (canary blocked), pre-commit runs `tools/check.py` (a failing test was rejected), boot route `tools/routes/boot.txt`
    (smoke ok on the original ROM).
  - Phase 1 recon: `docs/re/` — Shift-JIS text, ASCII event-script bytecode with arg-length table, control codes,
    script pointer table 0x420000 + string tables, 16×16 4bpp font (VWF needed), ROM map, EEPROM save, 1.06 MiB
    0xFF tail, 1,815 LZ77 blocks; graphics-text survey G1..G13 from tour + static sweep (338 sheets, all Codex-reviewed).
  - Phase 2 debug tool: `tools/debug/warp.lua` + `scenes.txt` (44 scenes: title, title menu, name entry/confirm,
    intro scroll, intro event, tutorial battle, credits, field, walk, ring menu, status, save, shikigami, map, party,
    shikigami talk, battle / win / lose, prologue + every chapter block's opening event, both endings, Drive event,
    4 NPC areas). `python -X utf8 tools/debug/warp_all.py` reaches all 44 from a cold boot (proof shots
    `work/qa/warp/scenes*.png`, states `work/states/<scene>.mss`). How it works + RAM map: `docs/re/debug.md`.
    Script helpers `tools/script_index.py`, `script_dump.py`, `script_refs.py`.
  - Phase 3 identity build: `build.py` repacks all 541 event scripts (`tools/evscript.py`: regions 0x419300..0x46A104
    + tutorial 0x6918E8..0x693978, NUL-terminated, slots) and 2,994 table strings (`tools/strtab.py`, 3,899 pointer
    words) → byte-identical ROM (sha1 47b04f67…, tests/test_build.py). Rule: fits its room → in place, else moves
    to 0x800000+ and is repointed. `build.py --relocate-all` moves everything; 44/44 warp scenes run on it and
    `tools/debug/romreads.lua` + `stale_reads.py` find 0 reads of vacated rooms (53,752 reads checked). Findings in
    `docs/re/text.md` (corrected arg table, pinned script 0x6918F4, 5-char shikigami name variables).
  - Phase 4 extract: `tools/textdb.py dump` → `script/*.json`, 57 files, 5,185 entries (2,191 script runs in
    `ev_<16 KiB block>` + `tutorial`, 2,994 strings in `str_<group>`), id = original offset, `jp`/`en`, `op` for
    runs, `max`/`pad`/`ptrs` for strings, gaiji readings in `notes`. `build.py` reads it; tests/test_text.py:
    JSON in sync with the ROM, every entry re-encodes to its bytes, ids = every run + string, no uncovered text-like
    run ROM-wide (`textdb.py coverage`), `en`=`jp` rebuilds the original, stale `jp` refused, dump keeps `en`.
    Findings in `docs/re/text.md` "Extracted text" (gaiji map: Cyrillic codes 0x8440.. = level-2 kanji).
  - Phase 5 so far: English font `tools/enfont.py` (93 own glyphs over the fullwidth Shift-JIS codes, encoder
    `encode_en` used by `textdb.overrides`), dialogue VWF `tools/vwf.py` (keystone; installed by `build.py`, off
    with `--no-engine` and in the identity tests), marker text `tools/marker.py` (`build.py --marker`). Proven on
    intro_event: `[4376A8] The quick brown fox…` drawn proportionally, 2 lines, pages. Helpers `tools/font.py`
    (glyph lookup/show), `tools/litref.py` (who loads a literal). Details: `docs/re/font.md`.
  - Phase 5 marker tour (2026-11-16): `warp_all.py build/marker.gba --out work/qa/mtour` reaches 43/44
    (tutorial_battle only needed more frames: scenes.txt now `frames=45000 deadline=44000`). `jp_left.py --sjis
    --gba-ptrs --orig` on the marker build: only `str_name_entry` (skipped on purpose) is left. Renderer catalogue
    from `tools/debug/glyphreads.lua` in `docs/re/font.md`: dialogue (VWF done), the window glyph routine
    0x080029F0 (every other fixed-cell text: menus, status labels, name tags, area names, battle messages, intro
    scroll), and the staff credits (CpuSet of whole glyph tiles). `tools/debug/ewram_watch.lua` = who touches the
    VWF state RAM.
  - Phase 5 renderers (2026-11-16, second session): `tools/debug/fontcalls.lua` lists every glyph-lookup caller
    (7, table in `docs/re/font.md` "Full renderer list"). VWF now on: dialogue, window glyph routine 0x080029F0
    (`WIN_SRC`, battle messages verified), strip renderers 0x080235D4 (intro scroll) / 0x08023E3C (credits) and the
    map-line renderer 0x0803A168 (name-entry screen) via one shared `line` plotter (`STRIP_SRC`), all verified in
    shots (`work/qa/wvwf*/c_*.png`). Probes `wincalls.lua` (window calls), `callshot.lua` (shot after a routine
    runs). `vwf._asm` rejects Thumb `adds rd, rn, #imm>7` (keystone mis-encodes it silently).
  - Phase 5 renderers (2026-11-16, third session): VWF on every glyph-lookup caller. OBJ menu cells 0x08014098
    (`STRIP_SRC` menu, status/shikigami labels verified), battle text 0x08110BAC (→ `mapline`) and its 2-row caller
    0x08110C88 replaced by `twoline` (split at newline 0x81AD or 224 px; the original's 60-byte stack buffer
    overflowed on long English). `marker.py`: table strings now fill the JP's cell width (16 px per JP char) with
    `[id]` + filler, so each field shows its pixel budget (marker ROM grows to 10 MiB: strings relocate).
    Shots: `work/qa/menu2/`, `work/qa/tb/`; full tour `warp_all.py build/marker.gba --out work/qa/mtour2`:
    44/44 scenes reached (sheets `work/qa/mtour2/scenes*.png`, not yet reviewed scene by scene).
  - Phase 5 small font (2026-11-16, fourth session): the battle speaker name tag is NOT the window routine but the
    small 8x8 font (resource type 12): 0x08111B50 → OBJ tiles 0x3DB..0x3DF (40 px), centred by byte count at
    0x0810F98A. Now `tag` (VWF, English small art `tools/ensmall.py`, drop shadow) + `tagw` (centre by pixels);
    small-font BG labels 0x08110AE8 → `smapline` (ceil(w/8) tiles: the original's unbounded tile-per-char write
    caused the stray "quick"/"hchc" fragments around the battle wheel). `build.py --qa ID=text` builds
    build/qa.gba with single-entry overrides. Verified "Kogenta"/"Ryuuko" tags + "View foe" label
    (`work/qa/tag2/z.png`, `work/qa/tag3/z.png`). New probes: `winopen.lua`, `objcalls.lua`, `linecalls.lua`,
    `oamfind.lua`. Details `docs/re/font.md` "Small font".
  - Phase 5 width gate (2026-11-16, fifth session): window data `tbl/windows.json` (13 variants: font, px, lines,
    chars cap, measured + shot / guess; files and ids mapped to variants) read by `tools/windows.py` (`budget`,
    `map`, `fill`, `show`), `tools/marker.py` (markers sized per variant and font, last dialogue line 216 px) and the
    new text lint `tools/lint.py` (in `check.py`: width per line, lines per page, chars cap, control-code multiset,
    glyphs, Japanese left, ordinal after a variable, empty en vs `script/keep_jp.txt`; `--marker` lints the marker
    text: 0 errors). Renderer map: `tools/debug/drawcalls.lua` + `windows.py map` (75 entries seen,
    `work/qa/dc/drawmap.tsv`). Measured: dialogue 224 / last line 216 (page-wait orb), battle window 220, area name
    28 chars, status labels = JP cells, battle tag 40 px small. Glyph torture line renders right
    (`work/qa/tort/`). Tests `tests/test_windows.py`. Details `docs/re/font.md` "Width gate".
  - Phase 5 width gate (2026-11-16, sixth session): measured `battle_2row` (224 + row 2 **208**; new `row_px` key,
    lint + marker use it), `intro_strip` 224, `credits` 240, `small_label` (JP tiles, all 10 callers read). Dialogue
    **speaker plate** found (0x0801EC54, own 5-tile loop) and given VWF + pixel centring (`vwf.plate`,
    `plate_patch`); `speaker_tag` measured 40 px. New scenes `menu_shiki_r1/r2/l1` (they show the same status
    page: R/L don't change it). `fontcalls.lua` takes `--var FONTTYPE=12`. Details `docs/re/font.md` "Width gate".
  - Phase 5 finished (2026-11-16, seventh session): shikigami pages reached (page u16 0x0200512C, d-pad LEFT;
    scenes `menu_shiki_p1..p4` replace r1/r2/l1); measured weapon 208 / skill 176 / technique 128 px, ability
    description = 2 rows of 224 (`line` plotter: newline → next 224 px row). `str_battle_kanji` = lookup keys
    for the super-move cut-in (variant `data_keys`, keep_jp); `build.py` JP_COPIES keeps a JP copy of
    techniques_b for the cut-in (test_cutin_keeps_japanese_keys). Name entry: grid → `gridline` (one centred
    glyph per cell; ABC tab = English letters, scene `name_entry_abc`), けってい label 0x0803A0A4 → `smapline`,
    default-name copy 2 → 5 halfwords, title 64 px, name ≤ 4 letters; prompts 40C540/40C560 = window (scene
    `name_back`). Debug menu + battle help = `unused` (dead / not reached, kept JP: D9). Link-cable menus =
    `link_window` (static: window system, needs a partner). Lint: keep_jp variants reject `en`; markers honour
    `chars`. New probe `tools/debug/mapcalls.lua`. keystone gotcha: no sp-relative byte/halfword access
    (`_asm` rejects it). Details `docs/re/font.md` "names_list", "Name entry".
  - Phase 6 set-up (2026-11-16, session 8): `glossary.md` filled (rulings D1-D4, names, places, terms, kind names,
    per-shikigami voices), `docs/translator-brief.md`, `docs/style-reference.md`, `tools/batches.py` (skill asset,
    adapted: `{XXXX}` codes, pixel widths via `lint.py`, keep_jp skipped, `\n` escaped in TSV, batches in tracked
    `tl/`, grouped by event script; `merge` writes whole files only and reports the rest as held). `check.py` now
    also runs `batches.py check` (glossary). Batches: `tl/b001..b041.tsv` (split --size 3000), outputs
    `tl/bNNN.out.tsv`. Speaker hints: op `036 00000001` = the player (ボク); `098 00XX0000` = portrait XX.
  - Phase 6 session 9 (2026-11-16): b005-b009 translated (rest of the contract scenes, prologue dream, school
    morning, Grandpa's letter, Yamase fight); `docs/synopsis.md` started (who is who, plot so far); glossary: Shiki
    Points, Drive, summon chant, item-get/give formats, clan names, voices (glossary "Decisions from earlier batches").
  - Phase 6 session 10 (2026-11-16): b010-b015 translated and merged (Ryuji, Grandpa's old letter, Misasa,
    Nakamura, Yuma/Soma, the dam-lake base, Chiryu Building, Taiin Shrine and the Four Kings, Mahoroba's awakening);
    glossary "b010-b015" row (Four Kings, -dono, voices), synopsis extended with the cast and plot to ev_44C000.
  - Phase 6 session 11 (2026-11-16): b016-b020 translated and merged (1000 years ago with young Issei, Hiroko's
    hideout, Gosho training cave, Masaomi/Soma/Yuma lend shikigami, Taihaku Shrine + Yakumo, Fukumaden clan
    villages, Koryu's Great-Des-cent, altar guardians); glossary "b016-b020" row, synopsis steps 5-6. Polish
    candidates: Shiran's 知らん name pun (451DF8..451E56, "Dunno"/"Shiran" kept); the 0x15 portrait is Yakumo under
    op `036 00150001` but Kogenta under `098 00150000` (036 and 098 use different portrait banks).
  - Phase 6 session 12 (2026-11-16): b021-b028 translated (finale + Mahoroba sealed, post-game Hiroko/Jinryu, all
    town/school/Fukumaden NPCs, abilities, area names, battle messages, NPC names, credits, intro scroll, link
    menus, Bannai's seal tutorial, name entry, shikigami battle quotes 01/02 + half of 03); glossary "b021-b026"
    row (stats, conditions, battle fragments), synopsis step 7, `docs/polish.md` started. `oamfind.lua` takes
    `--var TLO=.. --var THI=..`: the speaker plate's text is OBJ 0/1 (tiles 0x68..0x6C, x 16/48, y 108); its
    frame is NOT an OBJ (BG layer).
  - Phase 6 session 13 (2026-11-16): speaker plate widened by engine (`vwf.plate_frame`: BG frame 6 → 8 columns
    with a banded fill, text OBJ 40 → 64 px, cap 56 px, centred on x 40; docs/re/font.md "Speaker plate widened",
    shots work/qa/plt/plates.png); b023-b026 merged (all of str_areas, str_battle_msgs, str_char_names,
    str_credits). b029-b033 translated (shikigami battle quotes 03-08; weapon/skill names and quote voices in
    glossary "b029-b033"); quotes03-07 merged. New probes `tools/debug/bgdump.lua`, `valwatch.lua`.
  - Phase 6 session 14 (2026-11-16): b034-b041 translated (quotes08-10, save menu, shikigami kinds + names, skills
    = named weapons, str_system, tech quotes 1-5, techniques a/b, tutorial help, weapons, Kogenta's tutorial hints,
    Bannai's lectures); all merged except the 3 held files. `batches.py merge ... --partial` merges a set of batches
    while holding back every file with a problem. Glossary "b034-b041" row (affinity, element, field, clash, Art).
    Gotcha: the Write/Edit tools strip trailing spaces, so a TSV row that must end in a space ("Now at level ",
    410C78 ": ") was fixed with a scratchpad script; check `cat -A` on such rows.
  - Phase 6 session 15 (2026-11-16): the 3 held files fitted and merged (b036/b037). Battle name tag moved to free
    OBJ tiles 0x3D3..0x3DA (`vwf.tag_tiles`: 6 literals 0x3DB of sprite 0x2F + the 4 resource-2 fill calls -> `fill7`;
    `tools/debug/vramfree.lua` proved the tiles unused in 5 battles), 56 px, centred on x 40 on the widened plate
    (stress "Tsuiga White": work/qa/tagq/z.png). windows.json: new variants `obj_flow` (kind + clan + page header
    flow by returned cells), `obj_room` (shikigami page labels, 96 px), `status_label` (48 px), `padded` (key items,
    0x080144F4). D10: "Shiki Pts", "Healfire", header の = "-". New probes `oamall.lua` (whole OAM + used tile
    ranges), `vramfree.lua`.
  - Phase 6 done (2026-11-16, session 16): reviewer pass with `codex exec` (read-only) over all 41 batches:
    `tools/pairs.py` (pairs files from script/ English, `work/review/bNNN.pairs.txt`) + `tools/review.py` (one codex
    run per batch, brief `docs/reviewer-brief.md`, reports `work/review/bNNN.review.md`, `--summary`). 0 Critical,
    88 Important (D1 honorifics on titles, 交替 = swap, weapon/item names, flattened old-man/courtly/bratty voices);
    all fixed as batch `tl/b042` (merged `--overwrite`), re-review of b042: Approved, 0 C/I. 113 Minors appended
    to `docs/polish.md`. Glossary "Reviewer pass" row.
  - Phase 7 session 17 (2026-11-16): phase 6 review fixed first (D11 title honorifics: 宗家さま "Grand
    Master-sama", 闘神士様 "Tojinshi-sama", 9 lines as `tl/b043`; glossary rows enforce them, `batches.py has_term`
    matches mixed kanji+kana terms before particles; shikigami names table in the glossary; ベエ = "-bee").
    **ROM gate** `tools/romgate.py` + `tbl/allowed_ranges.txt` + `tests/test_romgate.py` (in check.py): skill
    romdiff with the write log, text writes only in their own room / on extractor pointer words (and pointing at
    the new home), every other write inside an allowed range, no branch or literal into a `code` hook span
    (`dead=` exemptions for replaced routines). **Lint: 0 errors, 0 guessed budgets** (key-item bar measured,
    scene `menu_keyitem`; link window measured by its twin, the battle window; `{00C8}` budget = 80 px, worst-case
    5 kana, 0 overflows). Engine: Save/Load headers drawn contiguous (OBJ x step 36 → 16, was "Loa  d";
    `vwf.save_headers`); speaker plate reads shikigami names from ROM table 0x0812AEE0 (was the 5-char RAM copy;
    `vwf.plate_names`; "Kogenta" verified in work/qa/pname). New scenes `title_load`, `menu_keyitem`
    (`link_connect` can't reach the link option: lands on Load). `oamall.lua --var AT=frame`. 【ability】
    message checked: 64-byte buffers, longest "[Magnetic Burst Stream]" 23 chars, battle box: fine.
  - Phase 7 done (2026-11-16, session 18): **party-card names** were "Kogen" + HP digits because sprite cell 2 is
    shared with the widened speaker plate: names now on own OBJ tiles 0x3C0 + 8k (free outside battles, proven by
    `vramfree.lua` over all 53 scenes), VWF 64 px (`vwf.obj8_patch`, pname/ctile). **Size-8 labels** (page header
    → "Pick shikigami", page labels, Swap) → centred small VWF (`o8`); lint variants `obj8_cells`/`obj8_label`.
    **Enemy-side tag**: right plate widened leftwards to 8 columns, tag centred on x 200 (`vwf.plate_right`).
    **RAM-string OBJ labels** (status page player name was "R i k u") → VWF with the outline dropped (`menu`
    → `mram`). Full tour `work/qa/tour7` 53/53. Probes: `valwatch.lua FROM=`, `bgdump.lua AT=`. Details
    docs/re/font.md "OBJ cells size 8", "Enemy-side tag".
  - Session 19 (2026-11-16): phase 7 review (.harness/reviews/…-phase7.md) Important 1+2 fixed: lint now fails a
    dropped leading/trailing JP blank (variants `pad_free`: intro_strip, credits; waivers `script/blank_ok.txt`)
    and a stub last line < 6 chars (`script/stub_ok.txt` keeps interjections + ability multipliers); tutorial-help
    headers centred by leading spaces (220 px), credits title 1283F8 centred, " cut", 4 orphans rebalanced
    (425E90, 42DCF8, 4479F4, 46148C) + 12DC48. Minors 2+3 too (chars cap counts `{XXXX}` as 4, `started` gate
    dropped). Important 3: new scene `menu_party_swap` (party menu, A on card → swap list; `poke_after=` in
    warp.lua fakes 3 owned shikigami) reproduces the bug; probe `tools/debug/ramlog.lua` (RAM at frames).
  - Session 20 (phase 8): **Swap list fixed** (`vwf.swap_list`): cell ids > 662 are another resource type (bound
    0x02960000), so rows keep cell 2 (64 px) and get 8 own tiles (rows 0..7 at 0x21C + 8k, rows 8..9 at 0x3E0 +
    8(k-8), tile fn 0x08111BB0), row x 196 → 192, names via o8 cap 7 (Tsuiga White 53 px fits); scenes
    `menu_party_swap10` (10 widest names, work/qa/sw3). **Graphics** `tools/gfx.py` (decode/encode OBJ tile runs,
    letter with the small or big English font, in-place LZ77 compressor, `install` from build.py; `gfx.py show`):
    G2 title buttons, G4 Yes/No both states (scene `name_confirm_yes`); inkbox symmetric. **QA tooling**:
    `warp_all.py --seq 90 --hold 1500` = shot every 90 frames after the scene + `<scene>/sheet*.png` (full size);
    tours `work/qa/tour8` (EN) and `work/qa/tour_jp` (original); `work/qa/manifest.tsv` (qa_gate, glob sheet*.png);
    `tools/vqa.py` = codex (read-only) per chunk with EN + JP sheet, brief `docs/visual-qa-brief.md`, verdicts
    `work/qa/verdicts/chunk_NNN.tsv`. Helpers `tools/lzdump.py` (every LZ block → work/lz for vramfind),
    `tools/oaminfo.py` (sprites in a rect from an .oam.bin).
  - Session 21 (phase 8): fixed 14 of the 16 first-pass visual-QA issues. **Text**: `enfont.encode_en` took
    "[Weak]" / "[Swap]" / "[List]" for `[XXXX]` codes and wrote raw ASCII (affinity page showed no 【不利】
    label): tokens now need uppercase hex (test_bracketed_word_is_text_not_a_code); ch11 page break rewritten
    (45C890). **Engine**: Save/Load headers centred on the JP centre from the English width (`vwf.HEADERS`: the
    `movs` immediate is 2*(x+8)); RAM-string OBJ labels (`mram`: player name on status/key-item plates) centred
    in their cells (`measure` + `linex`). **Graphics** (`tools/gfx.py`, docs/re/graphics.md "Phase 8 redraws"):
    battle wheel + field ring menu labels, guard emblem (shield icon), 6 attack-tier plates, Attack Bonus plate,
    party card HP/ATK/POW (LZ 0x3B577C moved to free space; `gfx.LZ_PTRS`). D12: title copyright notice + battle
    SFX kana stay Japanese (revisit). New `tools/bgmap.py` (BG map entries of a ppudump). Checked in shots:
    work/qa/s21a (Load, Riku, [Weak], ch11), s21b (Save/Load), s21c (ring, party), bw2 (wheel, shield), bw4
    (plates).
  - Session 22 (phase 8): full re-tour `work/qa/tour9` (56/56, build a32b1108), manifest re-made from it (old one
    `work/qa/manifest_s20.tsv`, verdicts `work/qa/verdicts_s20/`), `tools/vqa.py` on 10 chunks: 71 ok, 6 issue.
    Handled: battle_win "Short / cut" → "Quick / input" (40F724/40F730, the L-button label of the 印 panel: shot
    work/qa/s22d/ql.png); ch13 Koryu page break (ev_45C000.json, "Ohoho, what have we here? / A visitor, way out
    in a place like this..."). Checked, not bugs: ch6_start empty box (a frame between pages; dense capture
    work/qa/s22a/box4.png shows page 4 "Taihaku Shrine" drawn); ch9_start garbled plate (Villager→Kogenta overlap
    for 1-2 frames, then clean: work/qa/s22b/plate*.png; cosmetic, in polish). Still open: battle_win ドォォン SFX
    kana (D12, kept) and the **tutorial Drive screen** (below). **Text coverage tooling**: `build.py` writes
    `build/strings.tsv` (5,185 ids → built address; `build(layout=)`, test_layout_maps_every_text_to_its_built_address),
    `warp_all.py --scenes FILE --var V`, `tools/debug/cover.py scenes|ranges|run|report` (one `script ID` scene per
    StartScript id holding text: 283; skill probe textcover.lua; report via the skill's textcover.py).
    `tbl/jp_known.txt` committed: `jp_left.py ... --known tbl/jp_known.txt` exits 0 (13 known runs).
  - Session 23 (phase 8): **tutorial Drive screen** fixed: the Drive shows the battle-wheel art (also in normal
    battles) scaled ~1.4x under a mask that blanks alternate scanlines; the battle wheel labels are now drawn with
    every big-font row doubled (`gfx.letter(tall=True)`, `wheel(text, tall=True)`, caps rows 6..23). "Attack" reads
    on the Drive (work/qa/s23a/z1.png) and the wheel (work/qa/s23b/z.png); the field ring keeps the normal height.
    Visual-QA brief: D12 items (copyright notice, battle SFX kana) are standing non-bugs. Full **tour10** with the
    text probe (`work/qa/cover/tour10`, 56/56, build 606f89ee) → manifest re-made (old: work/qa/manifest_s22.tsv,
    verdicts_s22/), 10 vqa chunks run. **Waivers** `docs/text_unshown.tsv` (361 rows: debug menu, battle help, cut-in
    keys, link-cable screens, name-entry glyph grid). **Quote picker** found: 0x08104E70 selects table r5 (0..9,
    literals 0x08104EDC..0x08104F34), entry r3 + 2*r4, pointer in r0 at 0x08104F3A; `tools/debug/quotecycle.lua`
    overrides it with each quote in turn (tested: work/qa/qc, one quote per ~800 battle frames). Tech-quote tables
    (str_tech_quotes, 0x408258..) hang off a per-shikigami table at 0x40A620 (85 words; reader not found yet: no
    literal load, find it with a read watch on 0x0840A620.. in battle).
- **Next (phase 8: QA in the emulator; done-when in the skill's table):**
  1. Read the session-23 vqa verdicts (work/qa/verdicts/chunk_*.tsv, log work/qa/vqa10.log); fix issues, re-verdict
     fixed sheets; `qa_gate.py check work/qa/manifest.tsv work/qa/verdicts` must exit 0.
  2. **Text coverage** (`cover.py report` → work/qa/cover/report.txt; now 2342/5185 shown, 97 waived, 2746 failing):
     - quotes 1408: run quotecycle.lua in parallel battles (`START=t*1000+i`, ~50 quotes per job, a long hold, keep
       the battle alive: poke the enemy HP each frame, find its address with valwatch), output under
       work/qa/cover/ so the report counts it, plus the textcover probe.
     - tech quotes 258: find the reader of table 0x0840A620 and do the same.
     - techniques a/b 151, skills 53, weapons 10, abilities 31, kinds 22: shikigami pages for every shikigami
       (find the page's shikigami-id RAM byte, poke it per run; menu_shiki_p1..p4 scenes).
     - areas 103: map-menu area name per map (poke the map id), credits 38 (credits scene hold too short: scroll to
       the end), battle_msgs 58, system 23, tutorial 57 + tutorial_help 11 (play the tutorial battle further),
       save 6, menus2 12, script runs 551 (branches/NPC talk: per-script scenes with flags set).
     Waive only what is shown unreachable, with the reason.
  3. The rest of the done-when: graphics rows left
  (docs/re/graphics.md): G3 name-entry header/`けってい` (header already English as font text: check), G5 framed
  labels per screen (the Drive labels are done), G6 battle win/lose banners, G8, G11 town signs (low), G12 map
  labels, chapter cards / game over / credits: confirm each in tour sheets.
  Still unseen in a shot (add scenes): the party Swap label 1292CC, the
  non-battle right speaker plate (map 0x19E0BC: an event with a right-hand speaker), the 129064 column header
  row, the centred tutorial-help headers 410AE4.. (session 19 changed them; find when the battle shows them).
  Review minors left: pass `--known tbl/jp_known.txt` to jp_left.py in the release script; D10 "Shiki Pts" → "Shiki Points" via OBJ VWF.
  Translator notes to carry into the briefs: the check wants the exact `{0000}`/`{0010}` counts of the JP and a
  glossary term must not be split across a `{0000}` ("Spirit{0000}Stone Mound" fails); gaiji readings are in the
  entry's `notes` (Р=巫, 巫女 = shrine maiden); str_battle_msgs 40E534 starts with `\n` (code-built weapon/skill
  message); str_abilities rows split with `\n` (224 + 224 px); default name 40C51C ≤ 4 letters; keep_jp files
  (str_battle_kanji, str_debug_menu, str_battle_help, name-entry grid rows) stay empty.
  Engine items still open: name-entry cursor still at 16 px × length (cosmetic). The 5-char RAM name copy
  (0x020027B0 + 16i) now has no reader that shows English (plate reads ROM; text variables 0x0080..0x00C7 occur
  in no script).
  (EWRAM 0x0203FF00, the VWF state, is never read by the original game: safe.)
- **Known limits of the warp:** event scenes run over map 23 (the house) unless the script changes map itself
  (`map=` per scene overrides); which map normally hosts each event is not mapped yet (NPCs come from `/116`
  entries in map scripts 8000+). No GOD/NOENC yet (battles: mash wins; `poke=` for HP).
- **Open bugs:** see the session-23 vqa verdicts (Next 1). Cosmetic: speaker plate shows the old
  and new names overlapped for 1-2 frames on a speaker change (ch9_start; splot clears its tiles, so the overlap
  likely comes from the OBJ/tile update timing; check whether the original does the same).
  Cosmetic: field ring side labels are alpha-blended by the game, so the thin English strokes read fainter than
  the kanji did (a bolder 2-px font would help); shikigami-page cell gaps (docs/polish.md). (battle_win's scene
  shot is black in both tours: a fade frame, not a crash.)
- **Waiting on the user:** nothing. (Title logo kept Japanese per D5: no official English logo exists.)
