# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 2. Debug tool (phase 1 recon done 2026-11-16). Last build: none yet (no build.py).
- **Done:**
  - Step 0: ROM pinned (`rom.sha1`), MesenCE 2.2.1 + GBA BIOS in `tools/mesen/`, guard hook in `.claude/settings.json`
    (canary blocked), pre-commit runs `tools/check.py` (a failing test was rejected), boot route `tools/routes/boot.txt`
    (smoke ok on the original ROM).
  - Phase 1 recon: `docs/re/` — Shift-JIS text, ASCII event-script bytecode with arg-length table, control codes,
    script pointer table 0x420000 + string tables, 16×16 4bpp font (VWF needed), ROM map, EEPROM save, 1.06 MiB
    0xFF tail, 1,815 LZ77 blocks; graphics-text survey G1..G13 from tour + static sweep (338 sheets, all Codex-reviewed).
- **Next (phase 2, debug tool):** `tools/debug/warp.lua` + `tools/debug/scenes.txt`. Leads: script pointer table at
  0x420000 (827 entries, read at 0x0802A402) and the interpreter's current-script pointer in RAM (0x02002DE0 +
  0x38 × [0x02002DD6]); jumping the interpreter to a chosen script id from a cold boot is the likely warp. Story
  flags: find the `/123` condition variables. Scenes to cover: every graphics-text row in `docs/re/graphics.md`
  (title, name entry, battle, win/lose, area banners, status menus, credits, ending) plus one per chapter.
  Savestate after name entry: `work/states/intro.mss` (gitignored; recreate: `play.py --route` in
  `work/play/p1`, route `600 -;6 start;150 -;6 start;150 -;6 a;400 -;6 start;200 -;6 left;20 -;6 a;400 -`).
- **Open bugs:** none.
- **Waiting on the user:** nothing. (Title logo kept Japanese per D5: no official English logo exists.)
