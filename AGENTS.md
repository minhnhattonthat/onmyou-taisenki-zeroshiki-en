# Onmyou Taisenki Zeroshiki (GBA) English translation

Skill: translate-retro-game (Claude Code: plugin, enabled in .claude/settings.json; other agents: `<SKILL_DIR>/SKILL.md`). `python tools/skill.py` prints its folder; `"$(python tools/skill.py)"` works in bash and PowerShell; never paste a `plugins/cache/<hash>` path. Read its SKILL.md before ROM, text or QA work.

## Commands (run from repo root)
- Build:    `python -X utf8 build.py` -> build/onmyou_zeroshiki_en.gba (checks the dump against `rom.sha1` first; not written yet)
- Check:    `python -X utf8 tools/check.py` (tests + lint; the pre-commit hook runs this; needs `pip install pytest`)
- Smoke:    `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/onmyou_zeroshiki_en.gba --out work/qa/smoke --route tools/routes/boot.txt --smoke`
- Warp:     `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/onmyou_zeroshiki_en.gba --out work/qa/warp --script tools/debug/warp.lua --var "SCENE='<name>'" --frames 20000 --mash 40` (stops itself; scenes: `tools/debug/scenes.txt`, notes `docs/re/debug.md`; all scenes + states: `python -X utf8 tools/debug/warp_all.py`; never ask the user to play to a scene)
- Release:  `python -X utf8 tools/release.py` (patch + verify; never publish without the user)
- Clean:    `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)
- Hooks:    `git config core.hooksPath tools/hooks` once per clone.

## Paths
- Original ROM: `rom/Onmyou Taisenki Zeroshiki (Japan).gba` (8 MiB, AGB-BITJ; gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`). Emulator: this repo's own MesenCE in `tools/mesen/` (release 2.2.1, `python -X utf8 "$(python tools/skill.py)/scripts/fetch_emu.py" mesen` then `gba-bios`; gitignored). Savestates: `work/states/`.
- Text: `script/`. Tables: `tbl/`. Glossary: `glossary.md`. RE notes index: `docs/re/README.md`. Fonts and their licences: `docs/fonts.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- Subagents: dispatch the agent types (translator, reviewer, visual-qa, playtester, graphics) shipped by the plugin as `translate-retro-game:<type>` (Claude Code), `.codex/agents/` (Codex) or `.opencode/agents/` (opencode), never general-purpose.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Gotchas: see `docs/re/` and `docs/skill-gotchas.md`.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
