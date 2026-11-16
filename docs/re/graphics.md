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
| G3 | Name entry: header 名前入力, tabs カナ / かな / ABC, `START けってい` | guess: 0x2247F4+0x0000..0x6C00 framed labels; 0x140000+0x34000 (275:25) | **checked** (session 26): header "Enter Name" and `START OK` are English font text; the カナ / かな tabs stay (D9: they pick Japanese script, ABC tab is English) |
| G4 | Yes/No buttons はい / いいえ | **lz 0x3B4D40 (No selected) + 0x3B4FB0 (Yes selected)**, 64 tiles = two 64x32 OBJs; 0x3B577C is NOT Yes/No (slot frames with small kanji: screen unknown, check the tour) | **DONE** (session 20): big-font "Yes"/"No", both states, LZ77 rewritten in place (`gfx.lz77_compress`); scenes name_confirm / name_confirm_yes, shots work/qa/g8n/y.png, y2.png |
| G5 | Framed menu / status labels (dense outlined kanji+kana) | raw 0x22E3F4..0x2563F4 (2247F4+0x9C00..0x31C00; sheets 285..290) | **Session 28: mapped and DONE.** It is resource-table data (table 0x084028EC = (base, size) per type; descriptors via 0x08403DA4): type 34 = win banner 勝利 (done s26), **types 35..38 = battle banners 敗北 開始 先制 終** (64x64, redrawn YOU/LOSE, BATTLE/START, FIRST/STRIKE, END in `gfx.LABELS`; no reader seen in story battles, cold warps battle_forest/win/lose; session 29: 9,600 frames of walking on field_walk, npc_village, npc_park and ch1_mitsusa (work/qa/g78/enc_*) read none of 0x22E8B4..0x2320B4 either, so the game seems to have no random encounters and these are likely link battles, shown only as static renders work/gfx/banners*.png), **type 39 = the super-move cut-in kanji set** (256 32x32 cells, 128 KB; the technique name drops in vertically) → `tools/cutin.py` gives each name its own cells with rotated English (shot work/qa/g5/seal_en2: "NINE-SEAL ABYSS"; preview of all 75: `python -X utf8 tools/cutin.py show`). Types 40+ (0x2520B4..) = battle HUD art, no text. Probe: `tools/debug/gfxreads.lua` (first read per 0x200 block + shot). |
| G6 | Large dark lettering / logo pieces | lz 0x687AC4, 0x687E84 (268:15..30) | session 26: it is the title copyright notice art (kept, D12). The battle **win banner 勝利** is elsewhere: raw 0x22D8B4 (勝) + 0x22E0B4 (利), two 64x64 OBJs pal 9 at (6,16) / (106,48), **DONE** "YOU" / "WIN!" (`gfx.banner`, BANNER_FONT; shot work/qa/s26i/f000600.png). A loss has no banner: the battle fades to black and the script goes on (work/qa/s26j). |
| G7 | Outlined hiragana strip | lz 0x6884F8 (269:0..2) | **Session 29: not Japanese, no work.** With its tilemap (header 0x688754, LZ map 0x688758, 32x20) and palette 0x688730 it reads "Ms.RecvSuccessFlags" in English: a link-cable debug screen. Loaded by one case of the switch in 0x0800F27C (literal pool 0x0800F59C = tiles-4 / map / palette; the function is under the main loop via 0x08009238); no read of that literal in any of the 56 tour states (2500 frames each, work/qa/g78/lit_*). Render: work/qa/g78/g7map.png. |
| G8 | Brush-style kanji / stylized lettering | raw 0x310000+0x0000..0x8400 (291:1..292:0), 0x2247F4+0x2E800 (289:19) | **Session 29: no text, no work.** 0x310000.. = battle field tiles, then 64x64 OBJ frames of an effect animation (a burst/ring growing and fading, 0x311800..0x317000) and the HUD digits 0..9 at the end; read by BIOS CpuSet at battle start (battle_forest f1600, work/qa/g78/g8_battle_forest). Renders work/qa/g78/g8_raw.png, g8_obj.png. The 0x2247F4 part is G5 (done). |
| G9 | Battle UI | tour1 f008050: command label 攻撃１ is font text (0x1293B0); octagonal 印 input panel has no text | check HP/AP labels and result screens in the marker build |
| G10 | Dialogue speaker tab (blue tab above the box, e.g. バンナイ) | guess: font text drawn into a tab | confirm in the marker build |
| G11 | Town scenery signs: クリーニング, ピザ, 茶, 薬, 田中○科医院, アニメ・マガジン, emblems | lz 0x58E3DC, 0x590CC0, 0x593F80, 0x59C504, 0x5A0B84, 0x5A7810, 0x5A9C24, 0x5ABD24, 0x5B1A0C (171..179) | **DONE** (session 28, `tools/signs.py`, installed after the strings so string addresses don't move): every town map fits in the 512x512 BG2/BG3 maps, so a ppudump holds the whole map (VRAM tile = tile index in the block; pointer = 4-byte header, LZ77 at +4). 14 signs redrawn, tiles swapped by content in every town tileset: CLEANING ×3 (maps 21/60/67), RAMEN (来々軒, 29/67), DRUG ×2 (薬, 31/66; 16 px room: 3x5 micro font), VIDEO (ビデオ, 60), VEG (八百長, 62: one big letter per free 16-px slot), APARTMENTS (66), FLOW/ERS (花, 65), DENTIST (京中歯科医院, 67), vertical B-A-N-K (京中銀行, 66), BEEF (牛丼, 68). Survey misreads: "茶" = top half of 薬, "ピザ" = ビデオ, the idx 19 "cream sign" = a clock, idx 3 = stadium emblems (no text). Left as is (illegible at 8 px, D5 "readable ones"): blue post plates, the bath-house brush plate on map 21. Shots: work/qa/g11/signs_after_*.png (cold warps). Earlier notes: background art; translate the readable ones (D5), low priority. Session 27: these are entries 0,1,3,8,11,14,15,16,19 of the field tileset pointer table 0x0858D190 (loaded by 0x080089D4(idx, slot)); maps using them (`tools/debug/tilesetlog.lua`, sweep of maps 0..~240, shots work/qa/ts/maps/mapNNN/scene.png): idx 0 → maps 0,1,97,98; 1 → 2,99; 3 → 5; 8 → 21; 11 → 29,31; 14 → 60,62; 15 → 65,66; 16 → 67,68; 19 → 100 (warp: `field N`). Next: ppudump on those maps to find the sign tiles, redraw in the LZ block (gfx.py in-place compressor) |
| G12 | Map labels | lz 0x67EA80 (266:22), low confidence | **checked** (session 26): the world map (`menu_map`) has no graphic labels; place names are font text in the box |
| G13 | Small kana/symbol font | raw 0x1B12D4+0x0C00..0x2800 (283:13..20) | a second, smaller font; find its users in phase 5 |

## Phase 8 redraws (session 21, all in `tools/gfx.py` LABELS; find a sprite's source with ppudump + `tools/oaminfo.py`
+ `vramfind.py`, a BG's with `tools/bgmap.py`)
| Element | Source | English |
|---|---|---|
| Battle command wheel (G5/G9) 攻 防 逃 覧 替 | raw 0x22C434 + 0x200 k, 32x32 each | Attack / Guard / Run / List / Swap, big font ink 4, outline 2, drop 5, every row drawn twice (session 23: the Drive screen shows this art scaled ~1.4x under an alternate-scanline mask, which erased 1 px horizontal strokes) |
| Field ring menu 能 図 替 覧 記 | raw 0x3858CC + 0x200 k, same art | Status / Map / Party / List / Save (side labels are alpha-blended by the game: thin English strokes read fainter than the kanji) |
| Guard emblem 防 (2 animation frames) | raw 0x384A8C, 0x384C8C | shield icon (D12) |
| Attack-tier plates 攻撃1 攻撃2 必殺技1 必殺技2 超必殺技 超絶必殺技 (G9; NOT the font string 1293B0, which is the shikigami page) | raw 0x22B6B4 + 0x240 k, 72x16 | Attack 1/2, Special 1/2, Super Special, Ultimate Special (small font) |
| 攻撃ボーナス plate | raw 0x3856CC, 64x16 | Attack Bonus |
| Party card stats HP 攻 妖 (the "slot frames with small kanji") | lz 0x3B577C (moved to free space: recompressed 516 > 488 bytes; pointer 0x403CCC) | HP / ATK / POW, label boxes widened |
| Title copyright notice, battle SFX kana | not located / not redrawn | kept Japanese (D12) |

## Mid-game screens not yet seen (warp to each with the debug tool, phase 2/8)
Phase 2 warps now reach: battle win banner 勝利 (`battle_win`, graphic), loss (`battle_lose`), status (`menu_status`:
labels レベル/経験値/式点), save 記録 (`menu_save`), shikigami status しきがみせんたく with stat labels
(`menu_shikigami`), party (`menu_party`), world map (`menu_map`), staff credits (`credits`). Map them to G-rows in phase 5/8.
Chapter/area banners (area names are font strings at 0x40B6B4 — check whether a banner graphic also exists),
battle start / win / lose banners, game over, link-cable screens, status and shikigami-list screens, ending,
staff credits (credits text is font: 0x128418..), save/load screens.
