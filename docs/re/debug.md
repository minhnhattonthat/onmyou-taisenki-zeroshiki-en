# Debug tool: warp to any scene from a cold boot (phase 2)

Command (one scene): `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/onmyou_zeroshiki_en.gba --out
work/qa/warp --script tools/debug/warp.lua --var "SCENE='ch2_start'" --frames 20000 --mash 40`
(warp.lua stops the run itself `hold` frames after the scene is reached; it writes `scene.png` and `final.png`).
All scenes + savestates: `python -X utf8 tools/debug/warp_all.py [ROM] [--only a,b]` → `work/qa/warp/<scene>/`,
`work/states/<scene>.mss`, contact sheets `work/qa/warp/scenes*.png`. Exit 1 if any scene is not reached.
Scene list and syntax: `tools/debug/scenes.txt`. Script ids: `tools/script_index.py`; script bytecode:
`tools/script_dump.py ID [--text]`; who jumps to a script + flags it sets: `tools/script_refs.py ID`.

## Mechanism — verified (every scene in scenes.txt reached by warp_all.py, 2026-11-16)
- New game (fixed input route through title → name entry, ~1950 frames) ends in mode 6, which calls
  **StartScript(id)** at **0x0802A39C** with id 1001 (the intro). warp.lua hooks 0x0802A404 (r4 = script pointer,
  just loaded from the table) and points r4 at its own bytecode in EWRAM 0x0203F000 (scripts may run from RAM:
  table 0x41F848 already has RAM entries 0x0200A000). Injected: `/029 0000 FLAG 0001` per flag, `/144 MAP 0 0`,
  `/135 X Y 0 0` (player position, default 8,8), `/082` (fade in), optional raw bytecode, `/999`.
- Field = mode 2 (`0x02005074`). Event scenes: after 60 field frames write **0x020037BE = script id** and
  **mode = 8**: the field's own "run script [0x37BE]" state (0x0800FBF4), the same path the game uses.
- Credits: top-level state byte **0x03003523** = 63 at the title (3) runs the staff credits (0x08023680, table
  0x08128CF8). 59..61 = intro scroll (0x08022F98). 62 = new-game intro.
- Battles: injected `/035...` (args copied from a story battle) starts a battle from the field.

## RAM and code map
| Address | Meaning | State |
|---|---|---|
| 0x02005074 (u8) | field/game mode: 0 boot/title, 2 field, 6 new-game script, 7 script running, 8 run [0x37BE], 15 map-enter script | verified (jump table 0x0800F68C, 37 cases) |
| 0x03003523 (u8) | top-level state: 3 title, 59-61 intro scroll, 62 new game, 63-64 credits | verified |
| 0x020037BE (u16) | script id for mode 6/8 | verified |
| 0x02002E88 (u16) | current map id (new game: 23 = Riku's house); map-enter script = 8000+map (map ≥ 500: 7800+map) | verified (0x0800F75E, 0x0800FEA2) |
| 0x02002CB8 (256 B) | story flags, bit array, 2048 flags (`/029 0000 N V` sets, `/123 0000 N V S L` tests) | verified (0x080025C0/0x080025F4) |
| 0x02002DB8 (10 B) | temp flags (kind 1, 80 bits) | verified |
| 0x02002DD8 (u16) | opcode being run (hex value of the 3 digits: `/073` → 0x073) | verified |
| 0x02002DDC (u32) | current script pointer; 0x02002DD6 = call depth | verified |
| 0x02002E84 (u32) | interpreter "waiting" flag; the field leaves it 1 and a kicked script then stalls at `/230` (mode 34) — warp.lua clears it | verified |
| 0x02019938 (u16) | battle: player shikigami current HP (290 for Kogenta at start); poke 1 → knocked out on the next hit (battle_lose) | verified |
| 0x0802A39C | StartScript(id): 0..699 → table 0x41A058, 700..999 → 0x41F848, 1000..2999 → 0x41FE64, 8000+ → 0x41F2D8; double indirection | verified |
| 0x08018B84 | load map (r0 = map id) | verified (callers) |

## Opcodes used by the warp — verified by the warps
`/029 KIND VAR VAL` set flag (kind 0 story, 1 temp), `/123 KIND VAR VAL SCRIPT LABEL` jump if flag == VAL (kind 4 =
always; SCRIPT 9999 = this script), `/124 N` label, `/144 MAP X Y` change map, `/135 X Y 0 0` place player,
`/082` fade in, `/085` (not a fade-in), `/035 ...` battle, `/143` / `/142` event start / end, `/999` end.

## Script id blocks (from tools/script_index.py; story order is a guess from ids and text)
1001-1004 prologue; 1020-1071 ch1 (school, Misasa); 1100-1112 ch2; 1150-1162 ch3; 1200-1213 ch4; 1250-1262 ch5;
1300-1301 ch6; 1350-1364 ch7; 1400-1401 Fukumaden; 1450-1454, 1500-1504, 1550-1554, 1600-1604 shrine chapters;
1650-1653; 1700-1795 final, endings (1711, 1713) and post-battle shikigami contracts; 1800-1928 NPC talk;
700-704 Drive events; 8000-8337 map scripts; 0-23 map-link stubs.

## Probes (`--probe` for warp_all.py)
`tools/debug/romreads.lua` (reads of vacated text rooms), `glyphreads.lua` (who reads font data: renderer
catalogue in `docs/re/font.md`), `ewram_watch.lua` (who touches 0x0203FF00.., the VWF state; run on the original ROM).
