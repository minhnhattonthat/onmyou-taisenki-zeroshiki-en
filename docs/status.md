# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 5. Engine spike and marker build, in progress (VWF on 5 of 7 renderers). Last builds 2026-11-16:
  `build.py` (engine, JP text) sha1 f56ff550…, smoke ok; `build.py --marker` → build/marker.gba sha1 733552a0….
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
- **Next (phase 5):** VWF for the menu renderer 0x0801417B / 0x080142EB (status/save/shikigami, OBJ tiles) and
  battle results 0x08110BF3; identify the fixed-cell texts outside the lookup list (status digits, name tags
  "88"/"B2F4" — small font or sprites); then re-tour all 44 scenes on the marker build and measure each variant. (EWRAM 0x0203FF00 checked, 44 scenes, original ROM: never read by
  the game, only zero-filled by CpuSet at boot/title (f1, f272, f283, f605); a zeroed VWF state falls back to the
  game's cell position, so it is safe to keep there.) Then:
  check the 0x080144F4 string drawer (battle quotes, `pad` strings, newline 0x81AD) in a battle;
  widen the 5-cell shikigami-name copy; find code-built
  or base+immediate strings (Japanese that stays in the marker build; `jp_left.py` on build/marker.gba);
  identify `str_battle_kanji`; English name-entry grid; width gate per box variant (dialogue measured as
  x 8..232 = 224 px, last-column check pending; battle quotes, help 21, menus) recorded in a window-data file the
  lint will read; glyph torture line; add tests for enfont/vwf/marker (encode, widths table, ORIG asserts).
- **Known limits of the warp:** event scenes run over map 23 (the house) unless the script changes map itself
  (`map=` per scene overrides); which map normally hosts each event is not mapped yet (NPCs come from `/116`
  entries in map scripts 8000+). No GOD/NOENC yet (battles: mash wins; `poke=` for HP).
- **Open bugs:** none.
- **Waiting on the user:** nothing. (Title logo kept Japanese per D5: no official English logo exists.)
