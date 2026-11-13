import subprocess
import sys

from pypdf import PdfReader

from chordchart.parser import parse
from chordchart.render import render

ACTOR = open("examples/actor.chart").read()


def test_actor_renders_one_page(tmp_path):
    out = tmp_path / "actor.pdf"
    render(parse(ACTOR), str(out))
    r = PdfReader(out)
    text = r.pages[0].extract_text()
    assert len(r.pages) == 1
    for s in ["Actor", "Conan Gray", "Capo 4", "VERSE 2", "CHORUS", "BRIDGE",
              "E7", "G/B", "Dm", "x4", "doesn't resolve to C"]:
        assert s in text, s


def test_missing_header_parts(tmp_path):
    out = tmp_path / "x.pdf"
    render(parse("[A]\nC | G |"), str(out))
    assert "None" not in PdfReader(out).pages[0].extract_text()


def test_long_chart_paginates(tmp_path):
    src = "title: Long\n" + "\n".join(f"[A] Part {i}\nC | G | Am | F |" for i in range(40))
    out = tmp_path / "l.pdf"
    render(parse(src), str(out))
    r = PdfReader(out)
    assert len(r.pages) >= 2
    all_text = "".join(p.extract_text() for p in r.pages)
    assert all(f"PART {i}" in all_text for i in range(40))


def test_crowded_bar_fits():
    from chordchart.render import fitted_font_size
    assert fitted_font_size(["F#m7b5"], 40) < 20
    assert fitted_font_size(["C"], 120) == 20


def test_footer(tmp_path):
    out = tmp_path / "f.pdf"
    render(parse("footer: AGP Music\n[A]\nC |"), str(out))
    assert "AGP Music" in PdfReader(out).pages[0].extract_text()


def test_cli(tmp_path):
    out = tmp_path / "a.pdf"
    assert subprocess.run([sys.executable, "-m", "chordchart", "examples/actor.chart", str(out)]).returncode == 0
    assert out.exists()
    bad = tmp_path / "bad.chart"
    bad.write_text("[A]\nC | G :||")
    p = subprocess.run([sys.executable, "-m", "chordchart", str(bad), str(out)], capture_output=True, text=True)
    assert p.returncode == 1 and p.stderr.startswith("line 2:")
