import pytest
from pypdf import PdfReader

from chordchart.notation import rhythm_events
from chordchart.parser import ChartError, parse
from chordchart.render import render

PATTERN = "8d 8d 8u~ 8 8u 8d"


def test_stroke_and_tie_tokens_parse():
    s = parse(f"[A]\nstrum: {PATTERN}\nC |").sections[0]
    assert s.strum == PATTERN.split()


def test_events_carry_stroke_and_tie():
    ev = rhythm_events(PATTERN.split())
    assert [e.stroke for e in ev] == ["d", "d", "u", None, "u", "d"]
    assert [e.tie for e in ev] == [False, False, True, False, False, False]


def test_stroke_combines_with_accent_and_dot():
    ev = rhythm_events(["4.>d", "8u"])
    assert ev[0].accent and ev[0].dotted and ev[0].stroke == "d"


@pytest.mark.parametrize("bad", ["r4d", "r4~", "8x", "8d>", "8~d"])
def test_bad_stroke_tokens_are_errors(bad):
    with pytest.raises(ChartError, match=r"^line 2:"):
        parse(f"[A]\nstrum: {bad}\nC |")


def test_strum_before_any_section_is_allowed():
    chart = parse(f"title: T\nstrum: {PATTERN}\n\n[INTRO]\nC | G |")
    assert chart.sections[0].strum == PATTERN.split()
    assert chart.sections[1].label == "INTRO"


def test_strokes_render(tmp_path):
    out = tmp_path / "s.pdf"
    render(parse(f"title: T\nstrum: {PATTERN}\n\n[INTRO]\nC | G |"), str(out))
    r = PdfReader(out)
    assert len(r.pages) == 1 and "INTRO" in r.pages[0].extract_text()
