# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 5. Engine spike and marker build, in progress (VWF on every renderer incl. the small font; width gate next).
  Last builds 2026-11-16: `build.py` (engine, JP text) sha1 dbca5fa5…, smoke ok, check ok;
  `build.py --marker` → build/marker.gba sha1 ffe294b5….
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
- **Next (phase 5):** the width gate. (1) Window data file (e.g. `tbl/windows.json`: per variant px budget, lines,
  font big/small, measured/guess + shot; per-entry or per-file mapping) that `marker.py` and the lint both read:
  small-font strings (the 0x08110AE8 labels, e.g. 410C0C; the tag names = `str_shikigami_names` and any speaker
  names) must get markers sized in `ensmall` px (JP chars × 8 px, tag 40 px) — today they are sized in big-font px
  and overrun in the marker build. Find which string ids each of the 10 callers of 0x08110AE8 draws
  (`linecalls.lua` over all scenes). (2) Then measure each variant from `work/qa/mtour2` (EWRAM 0x0203FF00 checked, 44 scenes, original ROM: never read by
  the game, only zero-filled by CpuSet at boot/title (f1, f272, f283, f605); a zeroed VWF state falls back to the
  game's cell position, so it is safe to keep there.) Then:
  check the 0x080144F4 string drawer (battle quotes, `pad` strings, newline 0x81AD) in a battle;
  0x08014098 size-8 mode (small font, OBJ) still runs the original fixed cells;
  widen the 5-cell shikigami-name copy; find code-built
  or base+immediate strings (Japanese that stays in the marker build; `jp_left.py` on build/marker.gba);
  identify `str_battle_kanji`; English name-entry grid; width gate per box variant (dialogue measured as
  x 8..232 = 224 px, last-column check pending; battle quotes, help 21, menus) recorded in a window-data file the
  lint will read; glyph torture line; add tests for enfont/vwf/marker (encode, widths table, ORIG asserts).
- **Known limits of the warp:** event scenes run over map 23 (the house) unless the script changes map itself
  (`map=` per scene overrides); which map normally hosts each event is not mapped yet (NPCs come from `/116`
  entries in map scripts 8000+). No GOD/NOENC yet (battles: mash wins; `poke=` for HP).
- **Open bugs:** none. (battle_win's scene shot is black in both the old and new tours: a fade frame, not a crash.)
- **Waiting on the user:** nothing. (Title logo kept Japanese per D5: no official English logo exists.)
