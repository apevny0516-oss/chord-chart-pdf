"""Fonts and chord-name typography shared by the renderer and diagrams.

Text is set in Inter (bundled, SIL Open Font License), the free font closest to Apple's San
Francisco. Inter has no sharp/flat signs, so those two characters are drawn from DejaVu Sans
when it is installed, and fall back to plain '#' and 'b' otherwise.
"""
from __future__ import annotations

import os
import re
from typing import NamedTuple

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_DEJAVU = "/usr/share/fonts/truetype/dejavu"
SYMBOL_CHARS = "♯♭"          # sharp, flat
SYMBOL_SCALE = 0.92                    # DejaVu's signs are a little large next to Inter


class Fonts(NamedTuple):
    regular: str
    bold: str
    arrow: str
    accidentals: bool                  # real sharp/flat signs available
    symbols: dict                      # text font -> font that draws the sharp/flat signs


def load_fonts(font_dir: str = FONT_DIR, dejavu_dir: str = _DEJAVU) -> Fonts:
    def ttf(name: str, folder: str, file: str) -> bool:
        path = os.path.join(folder, file)
        if not os.path.exists(path):
            return False
        pdfmetrics.registerFont(TTFont(name, path))
        return True

    has_dejavu = (ttf("ChartSymbols", dejavu_dir, "DejaVuSans.ttf")
                  and ttf("ChartSymbols-Bold", dejavu_dir, "DejaVuSans-Bold.ttf"))
    symbols = {"Inter": "ChartSymbols", "Inter-Bold": "ChartSymbols-Bold",
               "ChartSans": "ChartSymbols", "ChartSans-Bold": "ChartSymbols-Bold"}
    if ttf("Inter", font_dir, "Inter-Regular.ttf") and ttf("Inter-Bold", font_dir, "Inter-Bold.ttf"):
        return Fonts("Inter", "Inter-Bold", "→", has_dejavu, symbols)
    if has_dejavu:                      # DejaVu has every glyph we need
        ttf("ChartSans", dejavu_dir, "DejaVuSans.ttf")
        ttf("ChartSans-Bold", dejavu_dir, "DejaVuSans-Bold.ttf")
        return Fonts("ChartSans", "ChartSans-Bold", "→", True, symbols)
    return Fonts("Helvetica", "Helvetica-Bold", "->", False, {})


_FONTS = load_fonts()
REGULAR, BOLD, ARROW = _FONTS.regular, _FONTS.bold, _FONTS.arrow
UNICODE = _FONTS.accidentals


def pretty(chord: str) -> str:
    """Chord name with real sharp/flat signs when a font can draw them."""
    if not _FONTS.accidentals:
        return chord
    chord = chord.replace("#", "♯")
    chord = re.sub(r"(?<=[A-G])b", "♭", chord)
    return re.sub(r"b(?=\d)", "♭", chord)


def _runs(text: str, font: str, size: float) -> list[tuple[str, str, float]]:
    """Split text into (piece, font, size) so sharp/flat signs come from the symbol font."""
    symbol_font = _FONTS.symbols.get(font)
    if not symbol_font or not any(ch in text for ch in SYMBOL_CHARS):
        return [(text, font, size)]
    return [(piece, symbol_font if piece[0] in SYMBOL_CHARS else font,
             size * SYMBOL_SCALE if piece[0] in SYMBOL_CHARS else size)
            for piece in re.findall(f"[{SYMBOL_CHARS}]+|[^{SYMBOL_CHARS}]+", text)]


def width(text: str, font: str, size: float) -> float:
    return sum(pdfmetrics.stringWidth(piece, f, s) for piece, f, s in _runs(text, font, size))


text_width = width


def draw_text(c, text: str, x: float, y: float, font: str, size: float, align: str = "left") -> None:
    """Draw text at (x, y) in the canvas's current fill colour. align: left, center or right."""
    total = width(text, font, size)
    x -= {"left": 0.0, "center": total / 2, "right": total}[align]
    t = c.beginText(x, y)              # one text object, so copy/paste keeps "F♯m" together
    for piece, f, s in _runs(text, font, size):
        t.setFont(f, s)
        t.textOut(piece)
    c.drawText(t)
