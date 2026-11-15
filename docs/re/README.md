# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dump in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| [text.md](text.md) | Shift-JIS encoding, ASCII event-script bytecode, control codes, script and string pointer tables, text ranges | encoding/format/ranges verified; label-based jumps a guess |
| [font.md](font.md) | 16×16 4bpp font, resource lookup, draw path | verified |
| [rom-map.md](rom-map.md) | ROM layout, LZ77, file table, EEPROM, free space | verified; 0xFF tail is a candidate |
| [graphics.md](graphics.md) | graphics-text survey (tour + static sweep) | survey done; sources partly guessed |

Prior work: no earlier English or other-language patch found for this game (searched 2026-11-16); the
anime (Onmyou Taisenki, 2004) had no official English release, so names follow D2 (Hepburn fallback).
Recon helpers: `tools/sjis_survey.py`, `tools/recon_strings.py`, `tools/lzscan.py`, `tools/gfx_sweep.py`,
`tools/gfx_review.sh`.
