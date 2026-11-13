import os

from pypdf import PdfReader

from chordchart import text as T
from chordchart.parser import parse
from chordchart.render import render


def test_inter_is_bundled_and_used():
    here = os.path.dirname(T.__file__)
    for name in ("Inter-Regular.ttf", "Inter-Bold.ttf", "Inter-LICENSE.txt"):
        assert os.path.getsize(os.path.join(here, "fonts", name)) > 1000
    assert (T.REGULAR, T.BOLD) == ("Inter", "Inter-Bold")


def test_pdf_embeds_inter_not_helvetica(tmp_path):
    out = tmp_path / "f.pdf"
    render(parse("title: Hi\nartist: Me\n[VERSE]\nC | G |"), str(out))
    fonts = {str(f.get_object()["/BaseFont"]) for f in PdfReader(out).pages[0]["/Resources"]["/Font"].values()}
    used = {f for f in fonts if f != "/Helvetica"}      # reportlab always lists its unused default font
    assert used and all("Inter" in f for f in used)


def test_accidentals_use_symbol_font_but_extract_as_sharp_and_flat(tmp_path):
    out = tmp_path / "a.pdf"
    render(parse("title: T\nkey: F#m\n[A]\nF#m | Bb7 | Ebmaj7 | C#m7b5 |"), str(out))
    page = PdfReader(out).pages[0]
    txt = page.extract_text()
    assert "F♯m" in txt and "B♭7" in txt and "E♭maj7" in txt and "C♯m7♭5" in txt
    assert "Key: F♯m" in txt


def test_mixed_font_width_adds_up():
    f = T.BOLD
    assert abs(T.text_width("F♯m", f, 20) - (T.text_width("F", f, 20) + T.text_width("♯", f, 20) + T.text_width("m", f, 20))) < 1e-6
    assert T.text_width("F♯m", f, 20) > T.text_width("Fm", f, 20)


def test_missing_font_folder_falls_back(tmp_path):
    assert T.load_fonts(str(tmp_path))[:2] != ("Inter", "Inter-Bold")
