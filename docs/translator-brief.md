# Translator brief - Onmyou Taisenki Zeroshiki (GBA, 2005)

You translate part of the Japanese script of Onmyou Taisenki Zeroshiki into English for a fan patch. An RPG tie-in
to the Onmyou Taisenki anime: the player (default name Riku, `{00C8}`) is a young Tojinshi who fights with shikigami
partners; light, boyish adventure tone with comic NPCs, rival factions (Tenryu, Chiryu, Jinryu) and yokai.
Work only on the batches named in your dispatch, one at a time in the order given, each to a passing check before the
next. Do all translation yourself; do not dispatch subagents.

## Read first
1. `glossary.md` - rulings, style rules (voice per first-person marker) and binding terms.
2. `docs/style-reference.md` - approved example pairs. Match this voice.
3. `docs/synopsis.md` - what is known of the plot and who is who.

## Input: `tl/<batch>.tsv`
`id<TAB>op<TAB>file<TAB>limit<TAB>Japanese`. op = the script op before the text (`073 0001` plain dialogue; `036`,
`098`, `124` set up a speaker portrait first); file = the script file; limit = box variant, px per line (line 1 /
last line of a page) and lines per page. Lines are in story order within a script (event runs share a scene).
`{0010}` = new page, `{0000}` = line break inside a page, `\n` = line break in a table string.

## Output: `tl/<batch>.out.tsv`, written with your file-write tool (not a shell heredoc)
`id<TAB>English`, every input id exactly once, same order. Plain ASCII: straight quotes, `...`; no tabs, no Japanese
or fullwidth characters. Copy every `{XXXX}` code exactly, same count and same page structure (the lint compares the
multiset); put each `{0000}` where the English line should break.

## Validate
`python -X utf8 tools/batches.py check <batch>` until it prints OK (pixel widths per line from the real font).
Then `python -X utf8 tools/batches.py merge <batch>` once every batch of the same script files is done (the lint
refuses a file with some English and some empty lines).

## Style
- Faithful: keep the information and order of ideas; adapt idiom, not meaning. Adapt wordplay so the joke lands.
- Keep the speaker audible (glossary "Style rules"). A line any speaker could have said is a mistake.
- Never abbreviate to fit; rephrase, or report `LONG: id`.
- No suffix glued to `{00C8}` (possessive 's is fine), no a/an right before it.

## Report
Files written and entry count; then any lines: `NEW TERM: jp -> en`, `UNSURE: id - note`, `LONG: id - note`.
