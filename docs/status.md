# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 5. Engine spike and marker build (phase 4 extract done 2026-11-16). Last build: from script/*.json with
  no `en`, sha1 47b04f67… = original, smoke ok.
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
- **Next (phase 5, engine spike + marker build):** font/VWF decision (16 px fixed cells, 14 chars/line, no ASCII:
  `docs/re/font.md`); an English encoding for `en` (today `en` goes through cp932 like `jp`); widen the 5-cell
  shikigami-name copy; marker build (`[id] text` in every entry) toured with the warp scenes; find code-built or
  base+immediate strings (Japanese that stays in the marker build); identify `str_battle_kanji`; English name-entry
  grid; width gate per box variant (dialogue, battle quotes `pad` 14, help 21, menus).
- **Known limits of the warp:** event scenes run over map 23 (the house) unless the script changes map itself
  (`map=` per scene overrides); which map normally hosts each event is not mapped yet (NPCs come from `/116`
  entries in map scripts 8000+). No GOD/NOENC yet (battles: mash wins; `poke=` for HP).
- **Open bugs:** none.
- **Waiting on the user:** nothing. (Title logo kept Japanese per D5: no official English logo exists.)
