import pytest
from chordchart.model import Roadmap, Shape
from chordchart.parser import parse, ChartError

ACTOR = open("examples/actor.chart").read()


def test_header():
    c = parse(ACTOR)
    assert (c.title, c.artist, c.capo, c.bars_per_line) == ("Actor", "Conan Gray", 4, 4)


def test_sections():
    c = parse(ACTOR)
    assert [(s.label, s.name) for s in c.sections] == [
        ("A", ""), ("A", "Verse"), ("A1", "Verse 2"), ("B", "Chorus"), ("C", "Bridge")]


def test_repeat_with_count():
    bars = parse(ACTOR).sections[1].items[0].bars
    assert [b.chords for b in bars] == [["C"], ["Am"], ["Em"], ["G"]]
    assert bars[0].repeat_start and bars[3].repeat_end and bars[3].repeat_count == 4


def test_endings():
    bars = parse(ACTOR).sections[2].items[0].bars
    assert len(bars) == 5
    assert bars[3].ending == (1, 2, 3) and bars[3].repeat_end
    assert bars[4].ending == (4,) and bars[4].chords == ["E7"] and bars[4].final


def test_two_chord_bar_simile_and_roadmap():
    ch = parse(ACTOR).sections[3]
    assert ch.items[0].bars[3].chords == ["Am", "G"]
    assert ch.items[1].bars[2].chords == ["%"]
    assert len(ch.items[2].bars) == 8 and ch.items[2].bars[7].final
    assert ch.items[3] == Roadmap("A1 -> B")


def test_diagram_lines():
    c = parse(ACTOR)
    assert c.custom_shapes == [Shape("G/B", "x20033", "x2--34"), Shape("G/B", "x2000x", None)]
    assert c.diagram_names == ["Dm"]


@pytest.mark.parametrize("bad", [
    "[A]\n||: C | {1,2: G :||",
    "[A]\nC | G :||",
    "tempo: 120\n[A]\nC |",
    "[A]\ndiagram G: x2003",
    "",
])
def test_errors_have_line_numbers(bad):
    with pytest.raises(ChartError, match=r"^line \d+:"):
        parse(bad)
