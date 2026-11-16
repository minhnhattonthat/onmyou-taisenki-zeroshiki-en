# Story reviewer brief - Onmyou Taisenki Zeroshiki (GBA)

You read one chapter of a JP->English fan translation straight through, in story order, the way a player
meets it. Per-batch reviewers already judged single lines with +-2 lines of context; your job is what they can't see.
Read-only: no edits, no git, no subagents, no web. Return the report as your final message; the controller saves it.

## Inputs (paths in your dispatch)
- Chapter file `work/qa/story/chapters/chNN_*.txt`: every line of the chapter in script order (`## file` headers
  split the 16 KiB script blocks), `>> id | speaker | JP` then `   EN` (and `   # note` for gaiji readings). Read ALL
  of it, in passes if large, before judging.
- Speaker column: the name plate the preceding op sets up. `Player` = the hero (ボク, polite boy; default name
  Riku, shown as `{00C8}` in text), `(no plate)` = narration, an NPC without a portrait, or the player thinking. A
  plate can stay up from the previous op, so judge the speaker from the line itself when they disagree.
- `docs/synopsis.md` (plot, who is who, late reveals), `docs/style-reference.md` (voice per character),
  `glossary.md` (rulings at the top, names, terms, voices), `docs/decisions.md` (the owner's rulings: honorifics
  kept, name order, etc.).
- Codes: `{0000}` line break, `{0010}` page break, `{00C8}` player name, `{00CB}`/`{00CC}` counts, `{00C9}`/`{00CA}`
  shikigami name variables. Lines are short on purpose (224 px dialogue box, 2 lines per page): terse is fine, and
  a suggestion must keep the line's `{0000}`/`{0010}` counts.
- Chapter order: ch01-ch08 follow the plot; ch09-ch11 are the shikigami contract side scenes (one short scene per
  shikigami, often a quiz or a race), each self-contained.

## Judge, across the whole chapter
- Continuity: each line follows from the one before; setups, callbacks and references back are kept; who knows what
  stays coherent; nothing gives a later reveal away early.
- Voice: each character sounds like the same person all chapter and matches their style-reference row: speech quirks,
  register, how they address others. Name the line where a voice drifts or goes neutral.
- Emotion: anger, fear, grief and comedy beats are as strong as the Japanese; a running gag keeps its punchline.
- Things players caught that reviewers missed: a joke losing half its gag; "1st" shown as "1th"; a name off by one
  letter; awkward stock phrases.
- Accuracy only where a line breaks one of the above; single-line accuracy was reviewed already.

## Report
### Issues
#### Critical (continuity break, reveal given away, wrong speaker)
#### Important (voice drift or flattened, emotional beat lost, setup or callback dropped, joke dead)
#### Minor (deferred to the polish pass)
Each: `- id - JP gist - problem - suggested EN` ("none" if empty). Don't inflate: a defensible rendering is not
Important.
### Assessment
`ok` (no Critical/Important) | `issue` - one sentence why. The controller writes this word into the chapter's verdict.
