# Polish list

Minor items deferred to one polish pass (translation.md §Review). Tick each `[x]`: fixed, or `waived: reason`.

- [ ] 451DF8..451E56 - Shiran's 知らん name pun ("Dunno"/"Shiran") could land better.
- [ ] quiz 鯛/恋 - kept as "koi"... love; revisit the pun.
- [ ] str_credits - staff name readings are best guesses (e.g. 東利文 Higashi/Azuma, 吉川成至, 松野勝太郎, 猪谷公彦,
      三戸亮, 金晏秀, 黒澤豪); check against any published romanisation.
- [ ] str_quotes03 12EF6C/12EFBC/12F0E4/12F27C - weapon names 北斗渡 "Hokuto Watari", 痛天角 "Tsutenkaku" (pun on
      Osaka's 通天閣 tower), 烈火翔 "Rekkasho", 逆鱗牙 "Gekirin Fang", 鉈 "hatchet": match `str_weapons` (b040/b041).
- [ ] 40D7B4/40D7BC, 40D964/40D970/40DC30, 40E3B4 - code-built battle message fragments ("The foe calls on" + name +
      " to descend!", "Attack " + "up!", "Both sides"): confirm assembly order and spacing in a battle shot.
- [ ] 40C600/40C63C, str_menus link-cable texts - layout unverified (needs a link partner).
- [ ] 129178 "Shiki Pts" (D10): widen the status-screen label OBJ (lr 0x0802EFFD, shows 48 px) and restore "Shiki Points" (50 px).
- [ ] 12B494 "Healfire" (D10): fine as a coined compound; revisit only if the shikigami header gets more cells.
- [ ] Battle name tag on the ENEMY side (side 1, e.g. Komaki in battle_win f3603, work/qa/tagq/battle_win/callshot_f3623): the right-hand plate is still 6 columns and tagw centres on x 40 for side 0, so side-1 text sits 8 px right of the plate centre and names over ~40 px clip at the screen edge. Widen the right plate (BG map) leftwards and centre per side.
