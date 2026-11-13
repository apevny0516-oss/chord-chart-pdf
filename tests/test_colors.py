import pytest
from reportlab.lib.colors import HexColor

from chordchart import render as R
from chordchart.parser import parse

YELLOW, GREEN, BLUE, PURPLE = "#FFF27A", "#A8F08A", "#8EC9FF", "#D6A8FF"
WHITE, GREY = "#FFFFFF", "#DDDDDD"


def hexed(label, name=""):
    return R.section_color(label, name).hexval().upper().replace("0X", "#")


@pytest.mark.parametrize("label,name,expected", [
    ("VERSE", "", YELLOW), ("VERSE 2", "", YELLOW), ("Verse", "", YELLOW),
    ("PRE-CHORUS", "", GREEN), ("PRE CHORUS", "", GREEN), ("Prechorus 2", "", GREEN),
    ("CHORUS", "", BLUE), ("CHORUS 1", "", BLUE), ("CHORUS 2", "", BLUE),
    ("BRIDGE", "", PURPLE), ("Bridge 2", "", PURPLE),
    ("INTRO", "", WHITE), ("OUTRO", "", WHITE),
    ("TAG", "", "#FFB3D1"), ("SOLO", "", "#FFC27A"), ("INTERLUDE", "", "#FFC27A"),
    ("POST-CHORUS", "", "#7FE8D8"),
    ("MYSTERY", "", GREY),
])
def test_word_labels_by_type(label, name, expected):
    assert hexed(label, name) == expected


def test_pre_chorus_is_not_mistaken_for_chorus():
    assert hexed("PRE-CHORUS") != hexed("CHORUS")
    assert hexed("POST-CHORUS") != hexed("CHORUS")


@pytest.mark.parametrize("label,name,expected", [
    ("A", "Verse", YELLOW), ("B", "Chorus", BLUE), ("C", "Bridge", PURPLE),
    ("A1", "Verse 2", YELLOW), ("B", "Pre-Chorus", GREEN), ("A", "Intro", WHITE),
])
def test_the_name_decides_when_it_is_a_known_section_type(label, name, expected):
    assert hexed(label, name) == expected


@pytest.mark.parametrize("label,expected", [("A", YELLOW), ("A1", YELLOW), ("B", "#7DF3FF"), ("C2", "#FF8AF3"), ("D", GREEN), ("E", GREY)])
def test_plain_letter_labels_keep_the_letter_colors(label, expected):
    assert hexed(label, "") == expected


def test_roadmap_boxes_use_their_sections_colors():
    chart = parse("[VERSE]\nC |\n[CHORUS 2]\nG |\n[A] Bridge\nD |\n-> VERSE -> CHORUS 2 -> A")
    colors = R.label_colors(chart)
    assert colors == {"VERSE": R.section_color("VERSE", ""), "CHORUS 2": R.section_color("CHORUS 2", ""),
                      "A": R.section_color("A", "Bridge")}


def test_headerless_section_has_no_colors():
    assert R.label_colors(parse("C | G |")) == {}


def test_every_color_is_light_enough_for_black_text():
    for c in R.SECTION_COLORS.values():
        r, g, b = HexColor(c).red, HexColor(c).green, HexColor(c).blue
        assert 0.299 * r + 0.587 * g + 0.114 * b > 0.6
