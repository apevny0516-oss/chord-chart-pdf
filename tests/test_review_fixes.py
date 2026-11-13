"""Regression tests for the final-review findings."""
import pytest

from chordchart.model import Roadmap
from chordchart.parser import ChartError, parse
from chordchart import render as R
from chordchart.text import BOLD, width


# 1. crowded bars never overlap barlines, and stay readable
@pytest.mark.parametrize("line", [
    "||: B7 Em A7 F#m7b5 :|| x2",
    "C | G | Am7 D7 Gmaj7 | C#m7b5 | D | E |",
    "C | G | Am7 D7 Gmaj7 Cmaj7 | F |",
    "F#m7b5 Bbmaj7 C#m7b5 Ebmaj7 | F#m7b5 Bbmaj7 C#m7b5 Ebmaj7 | F#m7b5 Bbmaj7 C#m7b5 Ebmaj7 | F#m7b5 Bbmaj7 C#m7b5 Ebmaj7 |",
])
def test_crowded_rows_fit_at_readable_size(line):
    item = parse("[A]\n" + line).sections[0].items[0]
    rows = R.plan_rows(item, 4)
    assert sum(len(r.bars) for r in rows) == len(item.bars)
    for row in rows:
        assert row.size >= 12
        assert sum(row.widths) <= R.CONTENT_W + 0.01
        for bar, w in zip(row.bars, row.widths):
            assert R.bar_need(bar, row.size) <= w + 0.01


def test_simple_rows_keep_equal_bars_at_full_size():
    item = parse("[A]\n||: C | Am | Em | G :||").sections[0].items[0]
    (row,) = R.plan_rows(item, 4)
    assert row.size == 20 and len(set(round(w, 3) for w in row.widths)) == 1


# 2. long roadmap notes wrap instead of running off the page
def test_long_roadmap_wraps():
    text = "A -> B then play the outro twice softly and then fade out with the drummer on toms while the singer ad libs over the top"
    lines = R.roadmap_lines(Roadmap(text), {"A", "B"})
    assert len(lines) >= 2
    assert all(R.runs_width(line) <= R.CONTENT_W for line in lines)
    words = " ".join(v for line in lines for kind, v in line if kind == "text")
    assert words.split() == text.replace("->", "").split()[2:]


def test_short_roadmap_text_stays_one_run():
    (line,) = R.roadmap_lines(Roadmap("B (doesn't resolve to C)"), {"A", "B", "C"})
    assert line == [("arrow", ""), ("label", "B"), ("text", "(doesn't resolve to C)")]


# 3. text that isn't a chord is an error, not a bar
@pytest.mark.parametrize("line", ["C | G | -> B", "play softly here", "C | Bridge |"])
def test_non_chord_text_is_an_error(line):
    with pytest.raises(ChartError, match=r"^line 2:"):
        parse("[A]\n" + line)


def test_unicode_arrow_is_a_roadmap_and_unicode_accidentals_are_chords():
    s = parse("[A]\nF♯ m7 | B♭ |\n→ A → B".replace("♯ m7", "♯m7")).sections[0]
    assert [b.chords for b in s.items[0].bars] == [["F#m7"], ["Bb"]]
    assert s.items[1] == Roadmap("A -> B")


@pytest.mark.parametrize("chord", ["C", "F#m7b5", "Bbmaj7", "G/B", "D/F#", "Asus4", "Cadd9",
                                    "E7(#9)", "C5", "Bdim", "Caug", "N.C.", "%", "Am7", "C6/9"])
def test_real_chords_accepted(chord):
    assert parse(f"[A]\n{chord} |").sections[0].items[0].bars[0].chords == [chord]


# 4. endings are never silently dropped
@pytest.mark.parametrize("line", ["||: C | {1: G} Am :||", "||: C | {1:} :||"])
def test_bad_ending_is_an_error(line):
    with pytest.raises(ChartError, match=r"^line 2:"):
        parse("[A]\n" + line)


# 5. long titles don't collide with capo or diagrams
def test_long_title_moves_diagrams_out_of_header():
    chart = parse("title: Somewhere Over The Rainbow What A Wonderful World\n"
                  "artist: Israel Kamakawiwo'ole\ncapo: 5\n[A]\nC |\ndiagrams: C, G, Am, F")
    plan = R.header_plan(chart, R.shapes_for(chart))
    assert not plan.diagrams_in_header
    assert width(chart.title, BOLD, plan.title_size) <= plan.title_width
    assert plan.title_size >= 13


def test_ordinary_title_keeps_diagrams_in_header_at_full_size():
    chart = parse(open("examples/actor.chart").read())
    plan = R.header_plan(chart, R.shapes_for(chart))
    assert plan.diagrams_in_header and plan.title_size == 24


def test_huge_title_still_fits_its_width():
    chart = parse("title: " + "Very Long Song Title " * 8 + "\ncapo: 2\n[A]\nC |")
    plan = R.header_plan(chart, [])
    assert width(chart.title, BOLD, plan.title_size) <= plan.title_width


# 6. every common way of writing a repeat count works
@pytest.mark.parametrize("tail", [":|| x4", ":|| x 4", ":|| (x4)", ":|| 4x", ":|| X4", ":|| ×4", ":||\nx4", ":||\n(4x)"])
def test_repeat_count_spellings(tail):
    items = parse("[A]\n||: C | G " + tail).sections[0].items
    assert len(items) == 1 and len(items[0].bars) == 2
    assert items[0].bars[1].repeat_count == 4


def test_stray_count_without_repeat_is_an_error():
    with pytest.raises(ChartError, match=r"^line 3:"):
        parse("[A]\nC | G |\nx4")


# word labels ([CHORUS]) are grey; only letter labels (A, A1, B) get a letter color
def test_word_labels_are_grey():
    assert R.label_color("CHORUS") == R.label_color("INTRO") == R.HexColor(R.OTHER_COLOR)
    assert R.label_color("C") == R.label_color("C2") == R.HexColor("#FF8AF3")
    assert R.label_color("A1") == R.HexColor("#FFF27A")
