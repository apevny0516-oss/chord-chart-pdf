"""Draw an ASCII tab block as a real tab staff."""
from __future__ import annotations

import re

from reportlab.lib.colors import HexColor, black, white

from .model import Tab
from .text import BOLD, REGULAR, width

STRING_GAP = 9.5
NOTE_LINE_H = 10.0
MAX_COL = 8.0
MIN_COL = 3.4
LABEL_W = 12.0
PAD = 5.0


def tab_height(tab: Tab) -> float:
    return (len(tab.above) + len(tab.below)) * NOTE_LINE_H + (len(tab.strings) - 1) * STRING_GAP + 2 * PAD


def column_width(tab: Tab, avail: float) -> float | None:
    """Width of one tab column, or None when the tab can't fit in `avail`."""
    cols = len(tab.strings[0]) - tab.strings[0].index("|")
    col = min(MAX_COL, (avail - LABEL_W) / cols)
    return col if col >= MIN_COL else None


def draw_tab(c, tab: Tab, x: float, y: float, avail: float) -> float:
    """Draw with the top-left corner at (x, y). Returns the height used."""
    col = column_width(tab, avail)
    origin = tab.strings[0].index("|")            # raw column of the first barline
    bodies = [s[origin:] for s in tab.strings]
    cols = len(bodies[0])
    left = x + LABEL_W

    def cx(raw_col: float) -> float:              # centre x of a raw text column
        return left + (raw_col - origin + 0.5) * col

    c.saveState()
    top = y - PAD - len(tab.above) * NOTE_LINE_H
    bottom = top - (len(bodies) - 1) * STRING_GAP

    def notes(lines: list[str], first_baseline: float) -> None:
        c.setFillColor(black)
        for n, line in enumerate(lines):
            by = first_baseline - n * NOTE_LINE_H
            for m in re.finditer(r"[A-Za-z0-9.]+|[^\sA-Za-z0-9.]", line):
                word = m.group(0)
                if len(word) > 1 or word.isalnum():
                    c.setFont(REGULAR, 8)
                    c.drawString(max(x, cx(m.start()) - col / 2), by, word)
                elif word == ">":
                    ax = cx(m.start())
                    c.setLineWidth(0.9)
                    c.line(ax - 2.6, by + 5.5, ax + 2.6, by + 3.2)
                    c.line(ax + 2.6, by + 3.2, ax - 2.6, by + 0.9)
                else:
                    c.setFont(REGULAR, 8)
                    c.drawCentredString(cx(m.start()), by, word)

    notes(tab.above, y - PAD - NOTE_LINE_H + 3)
    notes(tab.below, bottom - PAD - 7)

    # string lines and labels
    c.setStrokeColor(HexColor("#666666"))
    c.setLineWidth(0.6)
    for r, s in enumerate(tab.strings):
        ly = top - r * STRING_GAP
        c.line(left, ly, left + cols * col, ly)
        label = s[:origin].strip()
        if label:
            c.setFillColor(HexColor("#555555"))
            c.setFont(REGULAR, 7)
            c.drawRightString(left - 3, ly - 2.4, label)

    # barlines and repeat dots, column by column
    c.setStrokeColor(black)
    c.setFillColor(black)
    for k in range(cols):
        chars = {b[k] for b in bodies}
        if chars == {"|"}:
            bx = left + (k + 0.5) * col
            if k == 0:
                bx = left
            elif k == cols - 1:
                bx = left + cols * col
            c.setLineWidth(1.1)
            c.line(bx, top, bx, bottom)
        if ":" in chars:
            span = top - bottom
            for frac in (0.36, 0.64):
                c.circle(left + (k + 0.5) * col, bottom + span * frac if span else top, 1.3, stroke=0, fill=1)

    # fret numbers and technique marks
    for r, body in enumerate(bodies):
        ly = top - r * STRING_GAP
        for m in re.finditer(r"\d+|[^-|:\s\d]", body):
            text = m.group(0)
            font, size = (BOLD, 9.5) if text.isdigit() else (REGULAR, 7.5)
            mid = left + (m.start() + len(text) / 2) * col
            w = width(text, font, size)
            c.setFillColor(white)
            c.rect(mid - w / 2 - 0.8, ly - 4, w + 1.6, 8, stroke=0, fill=1)
            c.setFillColor(black)
            c.setFont(font, size)
            c.drawCentredString(mid, ly - size * 0.36, text)
    c.restoreState()
    return tab_height(tab)
