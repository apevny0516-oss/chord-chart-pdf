import pytest
from pypdf import PdfReader

from chordchart import render as R
from chordchart.diagrams import LIBRARY, barres
from chordchart.model import BarLine, Roadmap, ScaleDiagram, Shape, Tab
from chordchart.parser import ChartError, parse


# ----- parser -----

def test_strum_line_with_note():
    s = parse('[A]\nstrum: 8> 8 8 8> 8 8 8> 8 "w/ palm muting"\nEm | G |').sections[0]
    assert s.strum == ["8>", "8", "8", "8>", "8", "8", "8>", "8"]
    assert s.strum_note == "w/ palm muting"
    assert len(s.items) == 1


def test_strum_without_note():
    s = parse("[A]\nstrum: 4 4 8 8 4\nC |").sections[0]
    assert s.strum == ["4", "4", "8", "8", "4"] and s.strum_note is None


@pytest.mark.parametrize("bad", ["strum: 8 8 banana", "strum: r4>", "strum:", "strum: 3 3"])
def test_bad_strum_is_an_error(bad):
    with pytest.raises(ChartError, match=r"^line 2:"):
        parse(f"[A]\n{bad}\nC |")


def test_rests_and_rhythm_groups_are_bar_items():
    bars = parse("[A]\nAm r4 r2 | E | (8> 8 8> 8) r2 ||").sections[0].items[0].bars
    assert bars[0].chords == ["Am", "r4", "r2"]
    assert bars[2].chords == ["(8> 8 8> 8)", "r2"] and bars[2].final


def test_fermata_is_kept_on_the_chord():
    bars = parse("[A]\nG | C(fermata) ||").sections[0].items[0].bars
    assert bars[1].chords == ["C(fermata)"]


def test_bars_without_a_section_header():
    c = parse("title: Layla\n||: C | % :||\nAm | Dm |")
    assert c.title == "Layla"
    assert [(s.label, s.name) for s in c.sections] == [("", "")]
    assert len(c.sections[0].items) == 2


def test_scale_line():
    item = parse("[A]\nC |\nscale D min pent: 1:5,8 2:6,8 3:5,7 4:5,7 5:5,8").sections[0].items[1]
    assert item == ScaleDiagram("D min pent", {1: [5, 8], 2: [6, 8], 3: [5, 7], 4: [5, 7], 5: [5, 8]}, 1, 12)


def test_scale_with_fret_range_and_high_frets():
    item = parse("[A]\nscale A minor: frets 3-9 6:5,8 1:5,8").sections[0].items[0]
    assert (item.first_fret, item.last_fret) == (3, 9)
    assert parse("[A]\nscale X: 1:12,15").sections[0].items[0].last_fret == 15


@pytest.mark.parametrize("bad", ["scale D: 7:5", "scale D: 1:5,x", "scale D:", "scale D: frets 9-3 1:5", "scale D: frets 6-9 1:5"])
def test_bad_scale_is_an_error(bad):
    with pytest.raises(ChartError, match=r"^line 2:"):
        parse(f"[A]\n{bad}")


TAB = """[BRIDGE]
tab:
                     simile...
e|------------------|-----|
A|:-4-4-4-4-4-4-4-4-|--3-:|
E|------------------|-----|
    >     >     >
   PM- - - - - - - -|

A | % |
"""


def test_tab_block():
    items = parse(TAB).sections[0].items
    tab = items[0]
    assert isinstance(tab, Tab) and isinstance(items[1], BarLine)
    assert tab.strings == ["e|------------------|-----|", "A|:-4-4-4-4-4-4-4-4-|--3-:|", "E|------------------|-----|"]
    assert tab.above == ["                     simile..."]
    assert tab.below == ["    >     >     >", "   PM- - - - - - - -|"]


@pytest.mark.parametrize("bad", ["tab:\n\nC |", "tab:\njust words here", "tab:\ne|----|\nB|--|"])
def test_bad_tab_is_an_error(bad):
    with pytest.raises(ChartError, match=r"^line \d+:"):
        parse("[A]\n" + bad)


# ----- rhythm layout -----

def test_rhythm_events_beam_eighths_in_pairs():
    ev = R.rhythm_events(["8>", "8", "8", "8>", "4", "r4"])
    assert [e.beam for e in ev] == [0, 0, 1, 1, None, None]
    assert [e.accent for e in ev] == [True, False, False, True, False, False]
    assert ev[5].rest and not ev[4].rest


def test_rest_breaks_a_beam_and_sixteenths_group_by_beat():
    assert [e.beam for e in R.rhythm_events(["8", "r8", "8", "8"])] == [None, None, 0, 0]
    assert [e.beam for e in R.rhythm_events(["16"] * 4 + ["8", "8"])] == [0, 0, 0, 0, 1, 1]


def test_bar_need_counts_rests_and_rhythm():
    bars = parse("[A]\nAm | Am r4 r2 | (8> 8 8> 8) r2 |").sections[0].items[0].bars
    assert R.bar_need(bars[1], 20) > R.bar_need(bars[0], 20)
    assert R.bar_need(bars[2], 20) >= R.rhythm_width(["8>", "8", "8>", "8"]) + 9


def test_fermata_does_not_widen_the_chord():
    a, b = parse("[A]\nC | C(fermata) |").sections[0].items[0].bars
    assert R.bar_need(a, 20) == R.bar_need(b, 20)


# ----- roadmap -----

def test_multiword_labels_are_boxed_in_roadmaps():
    (line,) = R.roadmap_lines(Roadmap("VERSE -> CHORUS 2 (no tag)"), {"VERSE", "CHORUS 1", "CHORUS 2"})
    assert line == [("arrow", ""), ("label", "VERSE"), ("arrow", ""), ("label", "CHORUS 2"), ("text", "(no tag)")]


# ----- barre -----

def test_barres_detected_from_fingers():
    assert barres(Shape("Dmaj7", "xx0222", "---111")) == [(2, 3, 5, "1")]
    assert barres(Shape("F#m", "244222", "134111")) == [(2, 0, 5, "1")]
    assert barres(LIBRARY["C"]) == [] and barres(Shape("G/B", "x2000x")) == []


# ----- rendering -----

def _text(tmp_path, src):
    out = tmp_path / "x.pdf"
    R.render(parse(src), str(out))
    r = PdfReader(out)
    return len(r.pages), "".join(p.extract_text() for p in r.pages)


def test_render_everything_together(tmp_path):
    pages, text = _text(tmp_path, 'title: T\n[VERSE]\nstrum: 8> 8 8 8> 8 8 8> 8 "w/ palm muting"\n'
                        "||: E | % | A | Am r4 r2 :||\n" + TAB[len("[BRIDGE]\n"):] +
                        "G | C(fermata) ||\nscale D min pent: 1:5,8 2:6,8 3:5,7\n-> VERSE")
    assert pages == 1
    for s in ["w/ palm muting", "simile...", "PM", "D min pent", "12", "Am", "VERSE"]:
        assert s in text, s
    assert "fermata" not in text and "r4" not in text and "8>" not in text


def test_no_header_block_for_an_unnamed_section(tmp_path):
    chart = parse("C | G |")
    assert len(R._blocks(chart)) == 1


def test_blocks_have_heights_for_new_items():
    chart = parse(TAB + "scale D: 1:5,8")
    kinds = [type(i).__name__ for i in chart.sections[0].items]
    assert kinds == ["Tab", "BarLine", "ScaleDiagram"]
    assert all(b.fixed > 0 for b in R._blocks(chart))


def test_tab_too_wide_is_an_error(tmp_path):
    wide = "[A]\ntab:\ne|" + "-" * 400 + "|"
    with pytest.raises(ChartError, match="tab"):
        R.render(parse(wide), str(tmp_path / "w.pdf"))


def test_chord_then_rests_keeps_the_row_evenly_spaced():
    item = parse("[A]\n||: F#m | % | A | Am r4 r2 :||").sections[0].items[0]
    (row,) = R.plan_rows(item, 4)
    assert row.size == 20 and len(set(round(w, 3) for w in row.widths)) == 1


def test_item_positions_stay_inside_the_bar():
    bar = parse("[A]\nAm r4 r2 |").sections[0].items[0].bars[0]
    xs = R.item_positions(bar, 10.0, 110.0, 20)
    assert len(xs) == 3 and xs[0] == 10.0 and xs == sorted(xs)
    assert xs[2] + R.item_width("r2", 20) <= 110.0
