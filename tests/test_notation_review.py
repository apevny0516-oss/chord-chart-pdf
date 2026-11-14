"""Regression tests for the notation-additions review."""
import pytest

from chordchart import notation, render as R, tab as T
from chordchart.model import BarLine, Roadmap, Tab
from chordchart.parser import ChartError, parse


class FakeCanvas:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*a, **k):
            self.calls.append(name)
            return self
        return record


# 1. a tab block with no blank line after it must not swallow the chart
def test_tab_block_ends_at_chart_content():
    c = parse("[A]\ntab:\ne|--0--|\nB|--1--|\n   >\nPM- - -|\nAm | G | C | D |\n-> A again\n[B] Chorus\nC | G ||")
    a, b = c.sections
    assert [type(i) for i in a.items] == [Tab, BarLine, Roadmap]
    assert a.items[0].below == ["   >", "PM- - -|"]
    assert (b.label, b.name) == ("B", "Chorus") and len(b.items) == 1


@pytest.mark.parametrize("after", ["% | G |", "||: C | G :||", "strum: 4 4", "scale D: 1:5", "→ B", "r4 r4 r2 |"])
def test_tab_block_ends_before(after):
    items = parse(f"[A]\ntab:\ne|--0--|\n{after}\n[B]\nC |").sections[0].items
    assert isinstance(items[0], Tab) and items[0].below == []


# 2. strum line never runs off the page
def test_long_header_wraps_strum_and_note():
    s = parse('[A] Verse with a really quite long section name here\n'
              'strum: 8> 8 8 8> 8 8 8> 8 r4 r4 8 8 8 8 "let every chord ring out and keep the right hand loose"\nC |').sections[0]
    rows = R.header_rows(s)
    assert len(rows) >= 2
    assert all(R.header_row_width(s, row) <= R.CONTENT_W for row in rows)
    assert [p for row in rows for p in row] == ["label", "name", "strum", "note"]


def test_short_header_stays_on_one_row():
    s = parse('[A] Verse\nstrum: 8> 8 8 8> 8 8 8> 8 "w/ palm muting"\nC |').sections[0]
    assert R.header_rows(s) == [["label", "name", "strum", "note"]]


def test_strum_too_long_for_the_page_is_an_error(tmp_path):
    with pytest.raises(ChartError, match="strum"):
        R.render(parse("[A]\nstrum: " + "16 " * 80 + "\nC |"), str(tmp_path / "x.pdf"))


# 3. strum placement
def test_second_strum_in_a_section_is_an_error():
    with pytest.raises(ChartError, match=r"^line 3:"):
        parse("[A]\nstrum: 4 4 4 4\nstrum: 8 8 8 8\nC |")


def test_headers_after_a_top_of_chart_strum_are_an_error():
    # a strum before any section heads the chart, so header lines must come first
    with pytest.raises(ChartError, match=r"^line 2:"):
        parse("strum: 4 4 4 4\ntitle: X\n[A]\nC |")


# 4. tab lines with unusual characters are still tab lines, or a clear error
def test_tab_technique_letters_are_string_lines():
    t = parse("[A]\ntab:\ne|--5t12--X--|\nB|--7h9p7-*--|").sections[0].items[0]
    assert len(t.strings) == 2 and not t.above and not t.below


def test_space_before_tab_bar_is_tolerated():
    assert parse("[A]\ntab:\ne |--0--|\nB |--1--|").sections[0].items[0].strings == ["e|--0--|", "B|--1--|"]


def test_unknown_tab_character_is_named():
    with pytest.raises(ChartError, match=r"^line 4:.*'@'"):
        parse("[A]\ntab:\ne|--5--|\nB|--@--|")


def test_tab_with_trailing_text_is_a_clear_error():
    with pytest.raises(ChartError, match=r"^line 2:.*tab"):
        parse("[A]\ntab: riff 1\ne|--0--|")


# 5. chords beside rests keep the row's font size
def test_chord_beside_rests_is_not_shrunk():
    item = parse("[A]\nCmaj7 r8 r8 r8 r8 r8 r8 r4 | G | C | D |").sections[0].items[0]
    (row,) = R.plan_rows(item, 4)
    left, right = 0.0, row.widths[0] - 13
    assert row.size == 20
    assert R.item_font_size(row.bars[0], "Cmaj7", left, right, row.size) == 20


# 6. wide tabs with two-digit frets are an error, not mush
def test_wide_two_digit_tab_does_not_fit():
    body = "|" + "-12-14-15-17" * 11 + "|"
    assert T.column_width(Tab(["e" + body]), R.CONTENT_W) is None
    assert T.column_width(Tab(["e|--0--3--5--|"]), R.CONTENT_W) == T.MAX_COL


# 7. annotation lines clear the fret numbers
def test_tab_annotations_clear_the_strings():
    lay = T.tab_layout(Tab(["e|--0--|", "B|--14-|"], above=["  PM"], below=["  >"]), 500.0)
    assert min(lay.above) - lay.top >= 6
    assert lay.bottom - max(lay.below) >= 12
    assert T.tab_height(Tab(["e|--0--|"], above=["x"])) > T.tab_height(Tab(["e|--0--|"])) + T.NOTE_LINE_H


# 8. fermata gets its own room when the bar also has an ending or a count
def test_fermata_with_ending_gets_extra_room():
    def fixed(src):
        item = parse("[A]\n" + src).sections[0].items[0]
        return R._bar_row(R.plan_rows(item, 4)[0]).fixed
    plain = fixed("||: C | G :||")
    assert fixed("||: C | {1: G} :||") > plain
    assert fixed("||: C | {1: G(fermata)} :|| x4") > fixed("||: C | {1: G} :|| x4")
    assert fixed("C | G(fermata) ||") == fixed("||: C | {1: G} :||")


# 9. a bare number in parentheses is not a rhythm figure
@pytest.mark.parametrize("src", ["||: C | G :|| (4)", "||: C | G :||\n(2)", "C | (8) |"])
def test_bare_number_group_is_an_error(src):
    with pytest.raises(ChartError, match=r"^line \d+:"):
        parse("[A]\n" + src)


# 10. dotted rests show their dot
@pytest.mark.parametrize("dur", [1, 2, 4, 8, 16])
def test_dotted_rest_draws_a_dot(dur):
    plain, dotted = FakeCanvas(), FakeCanvas()
    notation.draw_rest(plain, dur, 0, 0)
    notation.draw_rest(dotted, dur, 0, 0, dotted=True)
    assert dotted.calls.count("circle") == plain.calls.count("circle") + 1


def test_dotted_rest_in_a_bar_is_wider():
    assert R.item_width("r8.", 20) > R.item_width("r8", 20)
