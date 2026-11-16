"""Width gate data (tbl/windows.json) and the lint that reads it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import enfont  # noqa: E402
import ensmall  # noqa: E402
import lint  # noqa: E402
import marker  # noqa: E402
import textdb  # noqa: E402
import windows  # noqa: E402


def test_every_entry_has_a_variant():
    missing = [(f, e["id"]) for f, es in textdb.load().items() for e in es if windows.budget(f, e) is None]
    assert not missing


def test_variants_are_well_formed():
    d = windows.data()
    for name, v in d["variants"].items():
        assert v["font"] in ("big", "small"), name
        assert v["px"] == "jp" or isinstance(v["px"], int), name
        assert v["status"] in ("measured", "static", "guess"), name
        if v["status"] == "measured" and not v.get("keep_jp"):  # keep_jp = data, proven in the code, not a shot
            assert v.get("shot"), name
        if v["status"] == "static":
            assert v.get("note") and v.get("renderer"), name
    for target in list(d["files"].values()) + list(d["ids"].values()):
        assert target in d["variants"]


def test_markers_fit_their_budgets():
    assert lint.lint(marker.markers(textdb.load()), prose=False)


def test_keep_jp_variants_reject_english():
    e = {"id": "40EB5C", "jp": "荼", "en": "X"}
    assert not lint.lint({"str_battle_kanji": [e]})
    e["en"] = ""
    other = {"id": "40EB60", "jp": "楽", "en": ""}
    assert lint.lint({"str_battle_kanji": [e, other]})


def test_lint_catches_overflow_and_codes():
    e = {"id": "X", "jp": "あ{0000}い{0010}", "en": "W" * 60 + "{0010}"}
    assert not lint.lint({"ev_test": [e]})
    e["en"] = "Hi{0000}there you go{0010}"
    assert lint.lint({"ev_test": [e]})
    e["en"] = "Hi{0000}there{0000}more{0010}"  # 3 lines on one page
    assert not lint.lint({"ev_test": [e]})


def test_lint_catches_stub_last_line():
    e = {"id": "X", "jp": "あ{0000}い{0010}", "en": "Let's just beat{0000}him!{0010}"}
    assert not lint.lint({"ev_test": [e]})
    e["en"] = "Let's just{0000}beat him!{0010}"
    assert lint.lint({"ev_test": [e]})


def test_lint_catches_dropped_blanks():
    e = {"id": "X", "jp": "　　【交替】", "en": "[Swap]"}
    assert not lint.lint({"str_tutorial_help": [e]})
    e["en"] = "    [Swap]"
    assert lint.lint({"str_tutorial_help": [e]})
    t = {"id": "X", "jp": "ディレクター　　", "en": "Director"}  # credits: trailing pad is free
    assert lint.lint({"str_credits": [t]})


def test_bracketed_word_is_text_not_a_code():
    # "[Weak]" was taken for a [XXXX] token and written as raw ASCII (the affinity page showed nothing)
    assert enfont.encode_en("[Weak]") == enfont.encode_en("[") + enfont.encode_en("Weak") + enfont.encode_en("]")
    assert enfont.encode_en("{0010}[81AD]") == "{0010}[81AD]"


def test_fill_exact():
    for px in (40, 160, 220, 224):
        assert enfont.text_width(windows.fill_exact(px, "big", "[A]")) == px
    assert ensmall.text_width(windows.fill_exact(40, "small", "[")) == 40
