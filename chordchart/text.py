"""Fonts and chord-name typography shared by the renderer and diagrams."""
from __future__ import annotations

import os
import re

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_DEJAVU = "/usr/share/fonts/truetype/dejavu"
REGULAR, BOLD, UNICODE = "Helvetica", "Helvetica-Bold", False
if os.path.exists(f"{_DEJAVU}/DejaVuSans-Bold.ttf") and os.path.exists(f"{_DEJAVU}/DejaVuSans.ttf"):
    pdfmetrics.registerFont(TTFont("ChartSans", f"{_DEJAVU}/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("ChartSans-Bold", f"{_DEJAVU}/DejaVuSans-Bold.ttf"))
    REGULAR, BOLD, UNICODE = "ChartSans", "ChartSans-Bold", True

ARROW = "→" if UNICODE else "->"


def pretty(chord: str) -> str:
    """Chord name with real sharp/flat signs when the font has them."""
    if not UNICODE:
        return chord
    chord = chord.replace("#", "♯")
    chord = re.sub(r"(?<=[A-G])b", "♭", chord)
    return re.sub(r"b(?=\d)", "♭", chord)


def width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(text, font, size)
