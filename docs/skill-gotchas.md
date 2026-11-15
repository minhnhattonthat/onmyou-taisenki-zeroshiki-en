# Skill gotchas

One line per gotcha: the reference file it belongs in, then the fact.

- SKILL.md Step 0: in an Orca worker session the plugin was enabled but neither its skill nor its hooks loaded; adding the `hooks` block (stable `$HOME/.claude/plugins/marketplaces/...` path) to `.claude/settings.json` took effect live in the same session.
- emulator-qa.md: the guard hook blocks a whole Bash call whose text merely contains `sed -i` (even inside a piped JSON test), so the rest of that call (e.g. an `rm`) never runs.
- graphics.md §Survey: `codex exec -s read-only -i sheet...` works as the read-only sweep reviewer (~57 sheets per call); without "write in English" it answers in Japanese.
- platform-gba.md: Mesen `on_read` probes never show glyph reads when the game copies glyphs with BIOS CpuSet into a RAM buffer; trace the draw call's arguments in disassembly instead.
- emulator-qa.md §Debug tool: Mesen GBA Lua `emu.setState({["cpu.r4"]=X})` inside an exec callback changes the register live, so a script-engine game can be warped by pointing its "start script" routine at bytecode written to free EWRAM (no ROM patch, works on any build).
- emulator-qa.md §Debug tool: a `--var` key with an underscore (`until_op=`) silently failed a `(%w+)=` Lua pattern; use `[%w_]+`.
- emu.py: `--mash` starts as soon as the route queue empties, including a route a `--script` queued with L.press, so mash runs reach a warp's scene earlier than unmashed ones (frame numbers differ between runs).
- emu.py: `--sheet` writes only the first 15-16 frames when a run has more shots; run `sheet.py DIR --from --to` for the rest.
- pipeline.md §Identity: a byte-identical repack doesn't prove the pointer lists; also build a relocate-everything variant (vacated rooms 0xFF) and warp every scene with a ROM-read probe flagging reads of vacated rooms. Here it caught an empty string pointed at inside another string's NUL padding and a script that code finds by scanning forward from its slot.
- lua/probes/watch.lua: it logs once per PC, so a memcpy or copy loop hides every later address; for 'who still reads old text' log once per address instead (tools/debug/romreads.lua).
- platform-gba.md: Shift-JIS games can park extra (JIS level 2) kanji in unused font cells at Cyrillic/Greek codes (here 0x8440..0x8459): a text dump shows `Ф麟` for 麒麟. Render those cells from the font and write the readings into the dump's notes before translating.
- platform-gba.md: keystone (Thumb) can't resolve a label's address for you; put `b entry1` / `b entry2` at the blob start so each entry sits at a fixed offset (0, +2). A 16-byte `bx pc` + ARM `ldr ip,[pc]; bx ip; .word target|1` thunk reaches code past the 4 MiB BL range (ARMv4T `ldr pc` doesn't interwork).
