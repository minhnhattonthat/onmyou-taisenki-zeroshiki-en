#!/bin/sh
# gfx_review.sh FIRST LAST OUT: have codex (read-only) list Japanese text in sweep sheets FIRST..LAST.
# Sheets come from tools/gfx_sweep.py (work/gfxsweep/sheet_NNN.png, 2x zoom, 32 tiles x 32 rows of 8x8 tiles).
first=$1; last=$2; out=$3
args=""
i=$first
while [ "$i" -le "$last" ]; do
  f=$(printf 'work/gfxsweep/sheet_%03d.png' "$i")
  [ -f "$f" ] && args="$args -i $f"
  i=$((i + 1))
done
prompt="You are a read-only visual reviewer for a Game Boy Advance fan translation. Attached are contact sheets
sheet_${first}..sheet_${last} (in order, numbered from ${first}). Each sheet is raw 4bpp tile data in grayscale at 2x,
32 tiles per row, 32 tile rows (each tile row = 16 px tall). Most of it is art, noise, or maps. Your job: find every
place where Japanese writing (hiragana, katakana, kanji, or Japanese-style fullwidth labels) is drawn as GRAPHICS:
menu labels, buttons, banners, title logos, card or status labels, battle UI words, sprite text, signs.
Glyphs may be split across adjacent 8x8 tiles (a 16x16 character appears as 2 or 4 consecutive tiles), so look for
kana/kanji strokes, not only whole characters. Ignore pure Latin letters and digits unless they sit next to Japanese.
Write descriptions in English (quote any Japanese you can read). Reply ONLY with lines in this TSV form, one per finding, no prose:
sheet_number<TAB>tile_row(0-31)<TAB>what you can read or describe (e.g. 'katakana ステータス label', 'kanji title logo pieces')<TAB>confidence(high/med/low)
If a sheet has no Japanese, write: sheet_number<TAB>-<TAB>none<TAB>high
Every sheet number from ${first} to ${last} must appear at least once."
# shellcheck disable=SC2086
codex exec -s read-only --skip-git-repo-check -o "$out" $args -- "$prompt" > "$out.log" 2>&1
echo "done $first-$last exit=$?"
