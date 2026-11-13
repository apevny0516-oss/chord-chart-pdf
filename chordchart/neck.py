"""Horizontal fretboard diagram for scales."""
from __future__ import annotations

from reportlab.lib.colors import HexColor, black, white

from .model import ScaleDiagram
from .text import BOLD, REGULAR

STRING_GAP = 9.0
TITLE_H = 18.0
NUMBERS_H = 14.0
MAX_CELL = 40.0
OPEN_W = 12.0
INLAYS = {3, 5, 7, 9, 15, 17, 19, 21}
DOUBLE_INLAYS = {12, 24}
NUMBERED = INLAYS | DOUBLE_INLAYS


def scale_height() -> float:
    return TITLE_H + 5 * STRING_GAP + NUMBERS_H


def draw_scale(c, scale: ScaleDiagram, x: float, y: float, width: float) -> float:
    """Draw with the top-left corner at (x, y), centred in `width`. Returns the height."""
    cells = scale.last_fret - scale.first_fret + 1
    cell = min(MAX_CELL, (width - OPEN_W) / cells)
    neck_w = cells * cell
    left = x + (width - neck_w) / 2
    top = y - TITLE_H
    bottom = top - 5 * STRING_GAP

    c.saveState()
    c.setFillColor(black)
    c.setFont(BOLD, 11)
    c.drawCentredString(x + width / 2, y - 10, scale.name)

    def fret_x(fret: int) -> float:          # centre of a fret's cell
        return left + (fret - scale.first_fret + 0.5) * cell

    c.setFillColor(HexColor("#CFCFCF"))
    for fret in range(scale.first_fret, scale.last_fret + 1):
        if fret in INLAYS:
            c.circle(fret_x(fret), (top + bottom) / 2, 3, stroke=0, fill=1)
        elif fret in DOUBLE_INLAYS:
            c.circle(fret_x(fret), top - 1.5 * STRING_GAP, 3, stroke=0, fill=1)
            c.circle(fret_x(fret), top - 3.5 * STRING_GAP, 3, stroke=0, fill=1)

    c.setStrokeColor(HexColor("#777777"))
    c.setLineWidth(1.6)
    for k in range(cells + 1):
        c.line(left + k * cell, top, left + k * cell, bottom)
    c.setStrokeColor(black)
    if scale.first_fret == 1:
        c.setLineWidth(3.2)
        c.line(left, top + 0.3, left, bottom - 0.3)
    for s in range(6):
        c.setLineWidth(0.6 + 0.16 * s)
        c.line(left, top - s * STRING_GAP, left + neck_w, top - s * STRING_GAP)

    for string, frets in scale.dots.items():
        sy = top - (string - 1) * STRING_GAP
        for fret in frets:
            if fret == 0:
                c.setFillColor(white)
                c.setLineWidth(1)
                c.circle(left - 6.5, sy, 3, stroke=1, fill=1)
            else:
                c.setFillColor(black)
                c.circle(fret_x(fret), sy, 3.7, stroke=0, fill=1)

    c.setFillColor(HexColor("#555555"))
    c.setFont(REGULAR, 7.5)
    for fret in range(scale.first_fret, scale.last_fret + 1):
        if fret in NUMBERED or (fret == scale.first_fret and fret > 1):
            c.drawCentredString(fret_x(fret), bottom - 10, str(fret))
    c.restoreState()
    return scale_height()
