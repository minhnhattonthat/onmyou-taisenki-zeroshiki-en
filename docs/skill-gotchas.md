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
