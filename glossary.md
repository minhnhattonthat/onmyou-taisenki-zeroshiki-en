# Glossary - Onmyou Taisenki Zeroshiki

Binding for every translator and reviewer. Agents propose additions in reports; only the controller edits this file.
`tools/batches.py check` enforces the tables: a JP term in a line needs one of its EN forms (separated by ` / `).

## Rulings (asked of the user once; options and reasons in docs/decisions.md)
- Honorifics: kept, hyphenated (Yakumo-san, Riku-kun, Mahoroba-sama); 先生 as a title = "-sensei", as a job = "teacher".
  Name order: Western (given name first). (D1)
- Romanisation source: official English names where they exist (none known for this series), else Hepburn without
  macrons: ソウタロウ Sotaro, リュージ Ryuji, ユーマ Yuma, ソーマ Soma. (D2)
- Credits: English. (D3)
- Register / flavour: keep light Japanese flavour (shikigami, Tojinshi, -san, onmyoji terms); speech quirks carried
  by English devices (see Style rules). Sound effects: plain words with ! ("Hah!", "Ugh...").
- Abbreviations: full names and terms everywhere, prefer engine changes over shortening (D4).

## Style rules
- Punctuation map: 「」 -> "...", 『』 -> '...', … and ・・・ -> ..., ！？ -> !?, ～ -> drop or "~" only in sing-song
  speech, full-width ＨＰ -> HP.
- Control codes stay exactly as in the JP, same count: {0010} = new page (also closes the box), {0000} = line break
  inside a page (max 2 lines a page; line 1 <= 224 px, line 2 <= 216 px, ~45 / ~43 characters), {00C8} = the
  player's name (45 px, write no suffix after it: "{00C8}'s" is fine, "{00C8}th" is not).
- Plain ASCII only. No a/an right before {00C8}.
- First-person markers carry voice: オレ = rough boy ("I", contractions, "ya", "gonna"); ボク = polite boy;
  ワシ / わし = old man ("my boy", "eh?", "hmm"); 拙者 = samurai ("this one", formal, "indeed"); マロ = courtly
  noble ("We"/"I" with old-fashioned diction, "most", "pray"); キサマ = hostile "you", "bastard"-level contempt only
  when the scene is vicious; ～ニャ = cat quirk ("-nya" kept at sentence ends, sparingly); ～べ / なんねぇべ =
  rural dialect (dropped g's: "ya can't go in there").
- Tutorial / system lines: short, direct, second person.

## Characters
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| リク | Riku | 45px | default player name; text uses {00C8} | |
| ヤクモ | Yakumo | | Tenryu Tojinshi | |
| コゲンタ | Kogenta | | Byakko (white tiger) shikigami | |
| マホロバ | Mahoroba | | | |
| マサオミ | Masaomi | | | |
| ユーマ | Yuma | | | Yuuma |
| ソーマ | Soma | | | Souma |
| ソウタロウ | Sotaro | | | Soutarou |
| リュージ | Ryuji | | | Ryuuji |
| モモ | Momo | | | |
| ナヅナ | Nazuna | | | |
| ミササ | Misasa | | | |
| ヤマセ | Yamase | | | |
| テル | Teru | | | |
| ヒロコ | Hiroko | | | |
| イッセイ | Issei | | | |
| オロチ | Orochi | | | |
| ランマル | Ranmaru | | | |
| ナギ | Nagi | | | |
| ウンリュウ | Unryu | | | |
| カゲロウ | Kagero | | | Kagerou |
| シラヌイ | Shiranui | | | |
| カムイ | Kamui | | | |
| ゲンタロウ | Gentaro | | shikigami | |
| ランゲツ | Rangetsu | | shikigami | |
| ブリュネ | Brune | | shikigami (Seiryu) | |
| フサノシン | Fusanoshin | | shikigami (Suzaku) | |
| リクドウ | Rikudo | | shikigami (Genbu) | |
| オニシバ | Onishiba | | shikigami | |
| ツイガ | Tsuiga | | shikigami; あか/くろ/しろ = Red/Black/White | |

Other shikigami and NPC names: Hepburn without macrons, as in `script/str_shikigami_names.json` and
`script/str_char_names.json` once translated (the tables are the reference).

## Places
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 京東町 | East Kyo Town | | 京 town names: direction + Kyo | |
| 京北町 | North Kyo Town | | | |
| 京西町 | West Kyo Town | | | |
| 京中町 | Central Kyo Town | | | |
| 京南町 | South Kyo Town | | | |
| 天神町 | Tenjin Town | | | |
| 伏魔殿 | Fukumaden | | the demon realm | |
| 鬼門塚 | Kimon Mound | | 鬼門 = Kimon (the demon gate) | |
| 太白神社 | Taihaku Shrine | | | |
| 太陰神社 | Taiin Shrine | | | |
| 御所 | the Gosho | | the palace | |
| 妙霊山 | Mt. Myorei | | | |
| 黄龍のいおり | Koryu's Hermitage | | | |
| 天流修練場 | Tenryu Training Hall | | | |
| 天流の分社 | Tenryu Branch Shrine | | | |
| 神流の隠れ家 | Jinryu Hideout | | | |
| 霊石塚 | Spirit Stone Mound | | | |
| 聖獣のほこら | Sacred Beast Sanctum | | ほこら = Sanctum | |
| 地流ビル | Chiryu Building | | | |
| 地流中継基地 | Chiryu Relay Base | | | |
| 謎の洞窟 | Mystery Cave | | | |
| 竹林 | bamboo grove / Bamboo Grove | | | |

## Items / skills / terms
| JP | EN | max | notes | Avoid |
|---|---|---|---|---|
| 式神 | shikigami | | never "familiar" | familiar |
| 闘神士 | Tojinshi | | shikigami fighters; plural Tojinshi | Toujinshi |
| 天流 | Tenryu | | faction | Tenryuu |
| 地流 | Chiryu | | faction | Chiryuu |
| 神流 | Jinryu | | faction | |
| 陰陽師 | onmyoji | | | |
| 宗家 | head family / Head of the Family / Grand Master | | head of a school | |
| 妖怪 | yokai | | | youkai |
| 邪気 | evil aura | | | |
| 聖獣 | Sacred Beast | | | |
| 白虎 | Byakko | | | |
| 朱雀 | Suzaku | | | |
| 青龍 | Seiryu | | | |
| 玄武 | Genbu | | | |
| 黄龍 | Koryu | | | |
| 相性 | affinity / matchup | | elemental matchup | |
| 連携攻撃 | combo attack / Combo | | | |
| 必殺技 | special move / super move | | | |
| 祭壇 | altar | | | |
| 霊石 | spirit stone | | | |
| 符 | talisman | | | |
| 経験値 | EXP / experience | | | |
| ＨＰ | HP | | | |
| 陰陽道 | Way of Onmyo | | | |
| 印 | seal | | the hand seals the player uses in battle | |
| 楓族 | Maple clan | | kind (族) names: English meaning + "clan" | |
| 消雪族 | Snowmelt clan | | | |
| 雷火 | Thunderfire | | kind; "Fusanoshin of Thunderfire" | |
| 式点 | Shiki Points | | the seal gauge shown under HP | |
| ドライブ | Drive | | the device that holds shikigami | |
| 式・神・降・神 | Shiki-gami, des-cend! | | summon chant, syllables split as in JP | |

## Decisions from earlier batches
- b001-b004 (contract scenes): けいやくした -> "You formed a contract with X."; けいやく -> contract; だんな -> "boss";
  item quotes keep "..." ("honey", "sake", "gold koban", "Peacock Fan", "Silver Sake Cup", "Golden Arrow").
- Shikigami voices so far: Goroza rough ("boss", dropped g's); Takamaru/Kotaro solemn; Bannai polite; Juzo/Fuji
  samurai "this one"; Kujirabee/Genpaku old man ("my boy", "eh?"); Sanemaro courtly "We/thou ... ojaru";
  Zukumaru/Masurao Kansai hustler ("pal", "ya"); Isoroku Satsuma ("lad", "I reckon"); Kuradayu archaic diviner;
  Chiyorozu sultry ("darlin'"); Namazubo DJ ("the great me", "Yo!"); Onishiba drifter ("this fella", "boss");
  Kantaro country boy ("y'know!" for っしょ); Brune soldier ("sir!"); Otochika baby-talk genius ("it iz", z for s);
  Komachi/Komaki/Jakuya bratty ("Stuuupid!").
- Shikigami kinds (str_shikigami_kinds) get English meanings: 霜花 Frost Flower, 埋火 Embers, 柊 Holly, 秋水 Autumn
  Water, 白銀 Silver, 豊穣 Harvest, 癒火 Healing Fire, 楓 Maple, 甘露 Nectar, 赤銅 Copper, 繁茂 Overgrowth, 大火 Blaze,
  榎 Hackberry, 消雪 Snowmelt, 青錫 Blue Tin, 芽吹 Sprout, 雷火 Thunderfire, 椿 Camellia, 凝寂 Stillness, 黒鉄 Black
  Iron; 麒麟/白虎/朱雀/青龍/玄武 keep their names (Kirin, Byakko, Suzaku, Seiryu, Genbu). The 32 px menu cells need
  engine work (phase 7) for these.
- b005-b009: item gets 『X』を手に入れた -> "You got{0000}the 'X'!" (capitalised item names: 'Honey', 'Gold Koban',
  'Sake', 'Peacock Fan', 'Fish', 'Earth Scroll', 'Silver Sake Cup', 'Golden Arrow', 'Snake Fang', 'Bamboo Leaves',
  'Seashell', 'Rainbow Stone', 'Momo's Lunch Box'); give prompts 「X」を、わたす？ -> 'Hand over the "X"?'.
- b010-b015: 四転王 -> "the Four Kings" (Mahoroba's: Kagero, Unryu, Nagi, Shiranui); 地流産業 -> "Chiryu Industries";
  京南ダム(湖) -> South Kyo Dam (Lake); 巫女 -> shrine maiden; ネング -> rice tax; 朝廷 -> the Imperial Court; ～どの ->
  "-dono" (Teru, Unryu); 降神 alone -> "descend"; trainer tally 通算で{00CB}勝 {00CC}敗 -> "Total: {00CB} wins,
  {00CC} losses."; 'Ryuji's Lunch Box'. Mahoroba speaks with the royal "We/Us". Voices: Ryuji rough health nut
  ("ya", veggies); Misasa rough girl ("Hyahaha"); Nakamura rural ("I am!", "shaddup", だ); Teru polite, always
  hungry; Otsuwa crone ("thou", "dearie", "Feh feh feh"); kid 0069 creepy ("Kikekekeke"); Ikejiri salaryman
  (courteous sales talk); 0072 woman "hon"; Ranmaru samurai "this one"/"thou"; Nagi Tosa dialect ("ye", "it were");
  0018 farmer ("Oh, what a fix, what a fix...").
  Honorific on the player's name is hyphenated ({00C8}-kun, {00C8}-dono): allowed, it is not an ordinal.
  Kinds as clans: 黒鉄族 Black Iron clan, 榎族 Hackberry clan, 柊族 Holly clan, 青錫族 Blue Tin clan, 癒火族 Healing
  Fire clan, 青龍族 Seiryu clan. 村井ヒロコ = Hiroko Murai (Murai-san). ソウタロウおじいちゃん = Grandpa Sotaro.
  Voices: Tsuruyakko brassy princess ("kiddo", "ya"); Ruri sultry ("little boy"); Izayoi/Kaniemon/Kabuto-O archaic
  "thou/thee"; Elekiter/Mingobee/Kofuku party guys ("man", dropped g's); Horin Kyoto sharp tongue ("ya", "dear");
  Raiden/Kongo/Rakusai old men ("my boy", "eh"); Itsumu である tic -> "so it is / so I do"; Jaja ぞよ tic -> ", I say";
  Hiyoshino せっちゃ lisp -> "thith one"; Ryukon polite "So sorry"; Kogenta rough ("ya", "trainin'", "the great me").
  Names: カブトオウ Kabuto-O, エレキテル Elekiter, ツイガ黒/赤 Tsuiga Black/Red.
- b016-b020: 大・降・神 -> "Great-Des-cent" (Koryu's one-time power-up, split like the summon chant); オーブ -> orb,
  霊玉 -> spirit orb; X のほこら -> "X Sanctum" (Byakko/Genbu/Seiryu/Koryu Sanctum); X の村 -> "X Village";
  聖獣の祭壇 -> "Sacred Beast Altar" (also the system prompt "Go to the Sacred Beast altar?"); 式神界 -> shikigami
  realm; 人間界 -> human world; 前「地流」宗家 -> former "Chiryu" Grand Master (Mahoroba); 四聖式神 -> Four Holy
  Shikigami; 修羅 -> "the path of war" / war demon; 一門のかんばん -> "my school's name"; どこかで、扉が開いたようだ ->
  "It seems a door opened somewhere."; よくぞ来た -> "So you have come!". Faction names keep their 「」 quotes.
  Voices: Yakumo friendly mentor (ボク, "Hahaha"); Nazuna cheerful shrine maiden ({00C8}-san, "Here I gooooo!");
  Gentaro (Kogenta's senior, "little brother in training") gruff-formal, calls the player {00C8}-dono; Koryu old hermit
  ("Fefefe", "my boy", "eh"); Kotaro solemn; Genbu villager rural ("ain't", "dooo!"); Shiran (シラン = 知らん pun:
  "Dunno..." / "Shiran", "The world's going to the dogs").
- Puns: 誇り/埃 (pride/dust) -> "pride" / lion pride; 鯛/恋 quiz kept as "koi"... love (polish candidate).
