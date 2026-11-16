"""Text lint (tools/check.py runs it): every entry with `en` is checked against its box variant (tbl/windows.json).

    python -X utf8 tools/lint.py [--marker] [-v]

Errors (exit 1): a line wider than the variant's px; more lines per page than the variant allows; control codes
differing from the JP (as a multiset); characters with no English glyph; Japanese left in `en`; an ordinal suffix
glued onto a variable ({00C8}th); a non-empty `jp` whose `en` is empty (unless the id is in script/keep_jp.txt);
any `en` in a variant marked keep_jp (strings the game uses as data); a leading or trailing blank of the JP that the
`en` drops (trailing padding is free in variants marked pad_free; script/blank_ok.txt waives an id, with a reason);
a multi-line page whose last line is under 6 characters, an orphan of a wrapped sentence (script/stub_ok.txt keeps
intended short replies). In the chars cap a {XXXX} variable counts as a 4-letter name.
Warnings (one summary line): entries with no variant, entries checked against a guessed budget (-v lists them).
--marker lints the marker build's text instead of script/ (a self-test of the window data: every marker must fit).
"""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import enfont  # noqa: E402
import ensmall  # noqa: E402
import textdb  # noqa: E402
import windows  # noqa: E402

CODE = re.compile(r"\{([0-9A-Fa-f]{4})\}")
TOKEN = re.compile(r"\[([0-9A-Fa-f]{4})\]")
JAPANESE = re.compile(r"[぀-ヿ一-鿿！-｠]")
ORDINAL = re.compile(r"\{00C[89A-C]\}(st|nd|rd|th)\b")
KEEP = ROOT / "script" / "keep_jp.txt"
BLANK_OK = ROOT / "script" / "blank_ok.txt"
STUB_OK = ROOT / "script" / "stub_ok.txt"
BLANKS = (" ", "　", "\t")  # "\t" = the wide blank glyph (enfont)
STUB = 6  # a wrapped paragraph's last line shorter than this many letters is an orphan


def id_list(path):
    """First word of every non-empty line (the rest of the line is the reason)."""
    if not path.exists():
        return set()
    return {ln.split()[0] for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}


def stub_lines(en, is_script):
    """Last lines of a multi-line page shorter than STUB characters (a code counts as a 4-letter name)."""
    out = []
    for page in split_pages(en, is_script):
        page = [ln for ln in page if ln.strip()]
        if len(page) >= 2 and len(CODE.sub("xxxx", page[-1]).strip()) < STUB:
            out.append(page[-1])
    return out


def var_px(code):
    return windows.data().get("vars", {}).get(code.upper(), 0)


def split_pages(en, is_script):
    """[[line, ...] per page]. Scripts: {0010} = new page, {0000} or \\n = new line. Tables: \\n = new line."""
    if not is_script:
        return [en.split("\n")]
    pages = []
    for page in re.split(r"\{0010\}", en):
        pages.append(re.split(r"\{0000\}|\n", page))
    if pages and pages[-1] == [""]:
        pages.pop()  # the box-closing {0010}
    return pages


def line_px(line, font):
    w, plain = 0, CODE.sub(lambda m: "\0" + m.group(1), line)
    parts = re.split(r"\0([0-9A-Fa-f]{4})", plain)
    for i, p in enumerate(parts):
        if i % 2:
            w += var_px(p)
        else:
            p = TOKEN.sub(lambda m: next((c for c, v in enfont.CODES.items() if v == int(m.group(1), 16)), "?"), p)
            w += (enfont if font == "big" else ensmall).text_width(p)
    return w


def lint(files, verbose=False, prose=True):
    """prose=False (marker text) skips the blank and stub rules, which judge translated wording."""
    errors, guessed, novar = [], [], []
    keep, blank_ok, stub_ok = id_list(KEEP), id_list(BLANK_OK), id_list(STUB_OK)
    for name, entries in sorted(files.items()):
        is_script = not name.startswith("str_")
        for e in entries:
            en, eid = e.get("en", ""), e["id"]
            if not en:
                data = (windows.variant(name, e)[1] or {}).get("keep_jp")
                if e["jp"].strip("　") and eid not in keep and not data:
                    errors.append(f"{name} {eid}: empty en")
                continue
            where = f"{name} {eid}"
            if (windows.variant(name, e)[1] or {}).get("keep_jp"):
                errors.append(f"{where}: data, not text (variant keep_jp): en must stay empty")
                continue
            if Counter(c.upper() for c in CODE.findall(e["jp"])) != Counter(c.upper() for c in CODE.findall(en)):
                errors.append(f"{where}: control codes differ from the JP")
            if JAPANESE.search(en):
                errors.append(f"{where}: Japanese left in en")
            if ORDINAL.search(en):
                errors.append(f"{where}: ordinal suffix after a variable")
            v0 = windows.variant(name, e)[1] or {}
            if prose and eid not in blank_ok:
                if e["jp"][:1] in BLANKS and en[:1] not in BLANKS:
                    errors.append(f"{where}: the JP starts with a blank, en does not (script/blank_ok.txt waives)")
                if e["jp"][-1:] in BLANKS and en[-1:] not in BLANKS and not v0.get("pad_free"):
                    errors.append(f"{where}: the JP ends with a blank, en does not (script/blank_ok.txt waives)")
            if prose and eid not in stub_ok:
                for line in stub_lines(en, is_script):
                    errors.append(f"{where}: stub last line {line!r} (rebalance, or list it in script/stub_ok.txt)")
            try:
                enfont.encode_en(en, string_table=not is_script)
            except ValueError as x:
                errors.append(f"{where}: {x}")
                continue
            b = windows.budget(name, e)
            if b is None:
                novar.append(where)
                continue
            px, lines, font, status = b
            if status != "measured":
                guessed.append(where)
            for n, page in enumerate(split_pages(en, is_script), 1):
                if len(page) > lines:
                    errors.append(f"{where}: page {n} has {len(page)} lines (max {lines})")
                v = windows.variant(name, e)[1]
                chars = v.get("chars")
                for k, line in enumerate(page):
                    lim = v.get("last_px", px) if k == len(page) - 1 else px
                    if v.get("row_px"):  # per-row budgets (row k of the box, not of the page's end)
                        lim = v["row_px"][min(k, len(v["row_px"]) - 1)]
                    n_chars = len(CODE.sub("xxxx", TOKEN.sub("x", line)))
                    if chars and n_chars > chars:
                        errors.append(f"{where}: {n_chars} characters > {chars} ({line[:40]!r})")
                    w = line_px(line, font)
                    if w > lim:
                        errors.append(f"{where}: {w} px > {lim} ({line[:40]!r})")
    for x in errors:
        print("ERROR", x)
    if verbose:
        for x in novar:
            print("no variant:", x)
        for x in guessed:
            print("guessed budget:", x)
    print(f"lint: {len(errors)} errors; warnings: {len(novar)} entries without a variant, "
          f"{len(guessed)} against a guessed budget")
    return not errors


def main():
    files = textdb.load()
    is_marker = "--marker" in sys.argv
    if is_marker:
        import marker
        files = marker.markers(files)
    sys.exit(0 if lint(files, "-v" in sys.argv, prose=not is_marker) else 1)


if __name__ == "__main__":
    main()
