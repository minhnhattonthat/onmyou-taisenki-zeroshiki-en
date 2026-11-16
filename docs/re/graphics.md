# Graphics-text survey (phase 1)

Sources: a tour (`work/qa/smoke-orig`, `work/qa/tour1`, play session `work/play/p1`: boot → title → name entry →
intro → first dialogue → battle tutorial) and a **static sweep** of every LZ77 block and raw graphics region:
`tools/lzscan.py` + `tools/gfx_sweep.py` → 338 sheets (`work/gfxsweep/`, `index.tsv` maps sheet:row → source),
each read by a read-only Codex reviewer (`tools/gfx_review.sh`, verdicts in `work/qa/gfxreview/c_*.tsv`; every sheet
has a line). Skipped by the sweep, with reason in `work/gfxsweep.log`: 24 duplicate blocks, one 192-byte palette,
the dialogue font 0x1B4E74..0x2247F4 (known Shift-JIS glyph set, `font.md`).

Phase 5's marker build re-checks this list: any Japanese still on screen there that is not a row here gets added.
"Source" = where the tiles live; "guess" until a redraw re-imports them and the screen changes.

## Tile-drawn Japanese (to redraw in phase 8)
| # | Screen / element | Source (sweep sheet:row) | Notes |
|---|---|---|---|
| G1 | Title logo 陰陽大戦記 / 零式 (+ furigana おんみょうたいせんき, ゼロシキ) | raw 0x140000+0x4400..0x8400 (269:26, 270:0) and/or 0x2247F4+0x7C00..0xD800 (284:24..285) | No official English logo → per D5 keep the Japanese logo; translate the furigana line / add English subtitle |
| G2 | Title menu はじめから / つづきから / つうしん | **raw 0x224874 / 0x224A34 / 0x224BF4**, 14 tiles each (32x16 + 16x16 + 8x16 OBJ), CpuSet to OBJ tiles 0x388.. at title | **DONE** (session 20): "New Game" / "Continue" / "Link", `tools/gfx.py` (small font, F outlined E, fill striped 9/8); shot work/qa/g8n/t.png |
| G3 | Name entry: header 名前入力, tabs カナ / かな / ABC, `START けってい` | guess: 0x2247F4+0x0000..0x6C00 framed labels; 0x140000+0x34000 (275:25) | play session p1 step 3; kana grid itself is font text (0x125E04 / 0x40C2A0) |
| G4 | Yes/No buttons はい / いいえ | **lz 0x3B4D40 (No selected) + 0x3B4FB0 (Yes selected)**, 64 tiles = two 64x32 OBJs; 0x3B577C is NOT Yes/No (slot frames with small kanji: screen unknown, check the tour) | **DONE** (session 20): big-font "Yes"/"No", both states, LZ77 rewritten in place (`gfx.lz77_compress`); scenes name_confirm / name_confirm_yes, shots work/qa/g8n/y.png, y2.png |
| G5 | Framed menu / status labels (dense outlined kanji+kana) | raw 0x22E3F4..0x2563F4 (2247F4+0x9C00..0x31C00; sheets 285..290) | ~160 KB of labels: menus, status screen, likely technique/skill name plates; identify per screen in phase 8 |
| G6 | Large dark lettering / logo pieces | lz 0x687AC4, 0x687E84 (268:15..30) | possibly chapter or battle banners (勝利 / 敗北?) |
| G7 | Outlined hiragana strip | lz 0x6884F8 (269:0..2) | probably name-entry or effect lettering |
| G8 | Brush-style kanji / stylized lettering | raw 0x310000+0x0000..0x8400 (291:1..292:0), 0x2247F4+0x2E800 (289:19) | low confidence; likely battle effect text (技名 / 降神) |
| G9 | Battle UI | tour1 f008050: command label 攻撃１ is font text (0x1293B0); octagonal 印 input panel has no text | check HP/AP labels and result screens in the marker build |
| G10 | Dialogue speaker tab (blue tab above the box, e.g. バンナイ) | guess: font text drawn into a tab | confirm in the marker build |
| G11 | Town scenery signs: クリーニング, ピザ, 茶, 薬, 田中○科医院, アニメ・マガジン, emblems | lz 0x58E3DC, 0x590CC0, 0x593F80, 0x59C504, 0x5A0B84, 0x5A7810, 0x5A9C24, 0x5ABD24, 0x5B1A0C (171..179) | background art; translate the readable ones (D5), low priority |
| G12 | Map labels | lz 0x67EA80 (266:22), low confidence | check in the tour |
| G13 | Small kana/symbol font | raw 0x1B12D4+0x0C00..0x2800 (283:13..20) | a second, smaller font; find its users in phase 5 |

## Mid-game screens not yet seen (warp to each with the debug tool, phase 2/8)
Phase 2 warps now reach: battle win banner 勝利 (`battle_win`, graphic), loss (`battle_lose`), status (`menu_status`:
labels レベル/経験値/式点), save 記録 (`menu_save`), shikigami status しきがみせんたく with stat labels
(`menu_shikigami`), party (`menu_party`), world map (`menu_map`), staff credits (`credits`). Map them to G-rows in phase 5/8.
Chapter/area banners (area names are font strings at 0x40B6B4 — check whether a banner graphic also exists),
battle start / win / lose banners, game over, link-cable screens, status and shikigami-list screens, ending,
staff credits (credits text is font: 0x128418..), save/load screens.
