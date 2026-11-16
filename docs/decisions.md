# Decisions

The user's rulings on scope, style and trade-offs, newest last. Read before asking the user anything; if a later
decision replaces one, mark the old one "replaced by D<n>" instead of deleting it. Binding term spellings live in
`glossary.md`; this file holds the why.

| # | Date | Question | Options offered | Decision and reason |
|---|---|---|---|---|
| D1 | 2026-11-16 | Honorifics and name order | keep (-san), drop; JP or Western order | Keep honorifics; Western order (given name first). Owner's standing answer for one-shot runs. |
| D2 | 2026-11-16 | Romanization source for names | official art, earlier patch, Hepburn | Official English names where they exist, else an earlier fan patch, else Hepburn without macrons. |
| D3 | 2026-11-16 | Credits | stay Japanese, translate | English. |
| D4 | 2026-11-16 | Abbreviations | engine work first (default), abbreviate | Engine work first (skill default); abbreviate only as a flagged last resort. |
| D5 | 2026-11-16 | Graphics text left in Japanese | none (default), list | Translate all of it (titles, menus, banners, cards); keep the Japanese logo only if no official English version exists. |
| D6 | 2026-11-16 | Specs and plans | need approval, pre-approved | Pre-approved: keep going through every checkpoint, report at the end. |
| D7 | 2026-11-16 | Existing saves / savestates | user's saves, none | None provided; build the debug tool as usual. |
| D8 | 2026-11-16 | Git identity | ask, preset | Already set by new-game.ps1; do not change it. |
| D9 | 2026-11-16 | Text players never see (str_debug_menu: leftover graphics-viewer menu; str_battle_help: rows whose only reader is dead code) | translate anyway, keep Japanese | Default taken by the agent (pre-approved run, D6): keep Japanese; lint rejects `en` there (variant `unused`, keep_jp). The name-entry kana tabs also stay (the ABC tab already has English letters). Revisit if the user wants them translated. |
| D10 | 2026-11-16 | Labels that still overflow after engine work (session 15) | widen the sprite, abbreviate | Default taken (D4/D6): engine first; the battle name tag was moved to 8 free OBJ tiles (56 px). Two last resorts, flagged in docs/polish.md: status-screen label 129178 = "Shiki Pts" (OBJ shows 48 px, "Shiki Points" is 50), kind 癒火 = "Healfire" (the shikigami page header has 8 cells: Healing Fire + Tsuruyakko needed 9). の in the header (12933C) = "-" ("Byakko - Kogenta"; "of" read backwards). Revisit if the status label sprite is widened. |
