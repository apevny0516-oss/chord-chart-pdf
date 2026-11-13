import re

import pytest
from reportlab.pdfgen.canvas import Canvas

from chordchart.diagrams import LIBRARY, draw_diagram, shapes_for
from chordchart.parser import ChartError, parse

ACTOR = open("examples/actor.chart").read()


def test_library_shapes_valid():
    for s in LIBRARY.values():
        assert re.fullmatch(r"[x0-9]{6}", s.frets)
        assert s.fingers is None or re.fullmatch(r"[-1-4]{6}", s.fingers)
    assert LIBRARY["Dm"].frets == "xx0231" and LIBRARY["C"].frets == "x32010"


def test_custom_wins_and_library_fills():
    names = [(s.name, s.frets) for s in shapes_for(parse(ACTOR))]
    assert names == [("G/B", "x20033"), ("G/B", "x2000x"), ("Dm", "xx0231")]


def test_library_not_duplicated_when_custom_given():
    chart = parse("[A]\nC |\ndiagram Dm: xx0231\ndiagrams: Dm, C")
    assert [s.name for s in shapes_for(chart)] == ["Dm", "C"]


def test_unknown_chord_named_in_error():
    with pytest.raises(ChartError, match="Zm9"):
        shapes_for(parse("[A]\nC |\ndiagrams: Zm9"))


def test_draw_returns_height(tmp_path):
    c = Canvas(str(tmp_path / "d.pdf"))
    assert draw_diagram(c, LIBRARY["Dm"], 72, 600, 60) > 0
