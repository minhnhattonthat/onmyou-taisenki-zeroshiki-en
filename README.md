# Onmyou Taisenki Zeroshiki English translation

Unofficial English fan translation of **Onmyou Taisenki Zeroshiki** (陰陽大戦記 零式; Game Boy Advance, Bandai,
2005): the source text and tools that build the patch.

**Just want to play?** Download the patch from [Releases](../../releases) and follow its README. This repository holds
no game data you can play; you need your own dump of the Japanese game.

**Found a bug?** [Report it](../../issues/new/choose): untranslated text, typos, overflow, crashes. Attaching a savestate
helps most.

## Translation status

| Part | Status |
|---|---|
| Dialogue / story (events, NPCs, shikigami contract scenes, tutorial) | Translated |
| Menus, items, skills, shikigami names and kinds, battle messages and quotes, save screen, area names | Translated |
| Graphics with text (title logo, menu buttons, battle banners and plates, Drive wheel, shop signs, super-move cut-in names) | Translated (redrawn) |
| Title-screen copyright notice, kana sound effects over battle hits | Left in Japanese on purpose ([decisions](docs/decisions.md) D12) |
| Name entry | English ABC tab added; the kana tab stays; default name Riku |
| Staff credits | Translated |

Known issues: the link-cable (two-player) menus are translated but untested with a second console; the speaker
plate can show two names overlapped for a frame when the speaker changes. See also [Issues](../../issues).

Base ROM: `Onmyou Taisenki Zeroshiki (Japan).gba` (No-Intro, AGB-BITJ), 8,388,608 bytes, CRC32 `66C29472`,
MD5 `89b14322fdd974ac1fe06c7b77c9dbff`, SHA-1 `47b04f671af34e8449856bdfc3acc76076c2273a`. The patched ROM is 9 MiB;
its CRC32 is in the release's README. Tested in Mesen 2.2.1. Start a new game.

## What's here

| Path | What it is |
|---|---|
| `script/` | Every text block: original Japanese and English. Translation fixes go here. |
| `glossary.md` | Binding names, terms and style rules. |
| `tools/` | Python build chain: extract, insert, lint, release. |
| `tests/` | pytest suite (ROM-dependent tests skip when the ROM is absent). |
| `docs/re/` | Reverse-engineering notes. |
| `docs/decisions.md`, `docs/status.md` | Rulings with their reasons; current progress and open bugs. |
| `docs/fonts.md` | Fonts used and their licences. |
| `AGENTS.md` | Instructions for coding agents (`CLAUDE.md` points to it). |
| `.codex/agents/`, `.opencode/agents/` | Subagent types (translator, reviewer, visual QA, playtester, graphics) for Codex and opencode; Claude Code gets them from the plugin. |

## Build your own patched ROM

Needs Python 3.12+ and your own dump of the Japanese game.

```sh
git clone https://github.com/minhnhattonthat/onmyou-taisenki-zeroshiki-en
cd onmyou-taisenki-zeroshiki-en
# copy your dump to: rom/Onmyou Taisenki Zeroshiki (Japan).gba
#   (8388608 bytes, SHA-1 47b04f671af34e8449856bdfc3acc76076c2273a; the build refuses any other dump, see rom.sha1)
python -X utf8 build.py                                # -> build/onmyou_zeroshiki_en.gba
python -X utf8 tools/check.py                          # tests + text lint
python -X utf8 tools/release.py                        # full gate + BPS patch + zip (needs the QA records in work/)
```

## Support

If you enjoy this translation, you can support my work on Ko-fi:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/minhnhattonthat)

## Licence

Tools and English translation: MIT. The original Japanese text in `script/` is Bandai's and is included only so
the translation can be checked against it. Onmyou Taisenki Zeroshiki is (c) Bandai, and the Onmyou Taisenki anime
(c) its rights holders; this project is not affiliated with them.
Do not share patched ROMs.

The translation was made with extensive AI assistance (Claude by Anthropic). Corrections are very welcome.
