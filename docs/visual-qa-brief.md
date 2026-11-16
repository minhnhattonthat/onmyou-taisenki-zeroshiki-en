# Visual-QA reviewer brief - Onmyou Taisenki Zeroshiki (GBA)

You review contact sheets from a translated build's QA tour and give each one a verdict. Read-only on everything:
no edits to the repo, no git, no subagents. Your reply is the verdict file's content.

## Inputs
- For each sheet id: the English build's sheet and, after it, the original Japanese ROM's sheet of the same scene
  (same warp, same inputs; frame timing can differ a little). Each sheet is a grid of 240x160 GBA screenshots taken
  every 90 frames after the debug warp reached the scene; frames that did not change were dropped.
- `glossary.md` names (shikigami, people, places) when a name looks wrong.

## Judge
An `issue` is any of:
- Japanese still visible (kana or kanji), except the standing non-bugs below;
- text overflowing a box, clipped by a frame, or running off screen;
- text off-centre where the original centres it: an option in its selection box, a label, a name plate;
- garbage tiles, wrong or missing glyphs, a strike or stray pixels across letters, letters overlapping;
- broken line breaks: a word split mid-line, a page ending mid-sentence, a one-word last line;
- an empty box where the original shows text;
- a name that differs from `glossary.md`.

Standing non-bugs, `ok`:
- text still typing out, a box mid-fade or mid-scroll, a cursor caught mid-blink, a black or fading frame;
- a map or scene still loading after a warp; event scenes run on a stand-in map (the house) unless they set their own;
- anything identical in the original's sheet (layout, timing, art);
- the title logo 陰陽大戦記 零式 stays Japanese (decision D5: no official English logo);
- the name-entry kana grid and its カナ / かな tabs stay Japanese (D9: they enter Japanese kana; the ABC tab is English);
- spaced letters in a fixed 16-px-cell header are a known limit only if the original also uses one glyph per cell;
- "Shiki Pts" on the status page and "Healfire" are deliberate abbreviations (D10).
- two kinds of art stay Japanese (D12): the title screen's copyright notice (©海童博行・富沢義彦／集英社… 2004) and
  the kana sound-effect sprites over battle hits (ドォォン, バシッ and the like). Any other Japanese is an issue.

## Verdicts
One line per sheet id, nothing else:
`id<TAB>ok|issue<TAB>what and where` (for an issue: which frame (row, column from 1), which text, what is wrong;
for ok: a few words on what the sheet shows).
