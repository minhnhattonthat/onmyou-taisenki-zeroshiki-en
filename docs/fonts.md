# Fonts

Every font or glyph sheet the build reads ends up inside the released patch, so its licence must allow that. One row
per file; a font with no known licence doesn't go into a release.

| File | Source (URL, version) | Licence | Redistributable in a patch | Used for | Changes made |
|---|---|---|---|---|---|
| tools/enfont.py (`ART`) | drawn for this project (2026-11-16) | same as repo | yes | dialogue VWF, every English glyph in the 16×16 font | outline added by the build |
| tools/titlelogo.py (`TITLE`, `ZERO`, `SHIKI`) | Anton Regular (https://github.com/google/fonts/tree/main/ofl/anton, fetched 2026-11-17), rasterised once to 1-bit '#' art; the TTF itself is not in the repo or the patch | SIL Open Font License 1.1 | yes (OFL allows embedding; only bitmaps of three words ship) | title logo "ONMYOU TAISENKI" (cap 24), "ZERO" / "SHIKI" (cap 26) | horizontally condensed (0.82 / 0.68 / 0.63), thresholded; outline and shadow added by the build |
| tools/ensmall.py (`ART`) | drawn for this project (2026-11-16) | same as repo | yes | English glyphs in the small 8×8 font (battle name tag VWF, small labels) | drop shadow added by the build |
