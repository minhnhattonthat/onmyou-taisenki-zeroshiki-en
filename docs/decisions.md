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
| D11 | 2026-11-16 | Honorifics on titles (phase 6 reviewer pass + phase 6 review) | keep the honorific on every title, translate titles as English titles | Default taken (D1/D6): D1 extends to the two titles the game treats as forms of address: 宗家さま/様 = "Grand Master-sama" ("Head of the Family-sama" also accepted), 闘神士様 = "Tojinshi-sama", 闘神士さん = "Tojinshi-san" (glossary rows, enforced by `batches.py check`). Other titles are translated as English titles with no suffix, because an English title already carries the respect: 姫様 "Princess", お師匠様 "Master", 族長様 "the chieftain", 朝廷さま "the Imperial Court", 坊ちゃん "little rich boy". |
| D12 | 2026-11-16 | Graphics left Japanese after the phase 8 visual-QA pass (session 21) | redraw everything (D5), keep some | Default taken (D5/D6): two kinds stay Japanese for now, flagged here to revisit: the title screen's copyright notice (©海童博行・富沢義彦／集英社・WIZ・サンライズ / 陰陽製作委員会・テレビ東京 2004: tile art, the rights holders' legal notice; ©BANDAI 2004 is already Latin) and the kana sound-effect art over battle hits (onomatopoeia drawn as effect sprites, not titles, menus, banners or cards). Battle/field Drive labels, the guard emblem (a shield icon: its 19 px interior can't hold "Guard"), attack plates and party-card stats are translated. Party-card stats use HP / ATK / POW (3-letter slots, like the original's HP). |
