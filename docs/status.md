# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 3. Identity build (phase 2 debug tool done 2026-11-16). Last build: none yet (no build.py).
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
- **Next (phase 3, identity build):** `build.py` that unpacks then repacks with no edits → byte-identical ROM, as a
  test. Script region 0x41FE58..0x46B000 + every script pointer (tables 0x41A058, 0x41F848, 0x41FE64, 0x41F2D8 are
  double-indirect: entry → u32 → script; plus the per-script u32 right before many scripts), string tables
  (`docs/re/text.md`), tutorial scripts 0x6930A4.. .
- **Known limits of the warp:** event scenes run over map 23 (the house) unless the script changes map itself
  (`map=` per scene overrides); which map normally hosts each event is not mapped yet (NPCs come from `/116`
  entries in map scripts 8000+). No GOD/NOENC yet (battles: mash wins; `poke=` for HP).
- **Open bugs:** none.
- **Waiting on the user:** nothing. (Title logo kept Japanese per D5: no official English logo exists.)
