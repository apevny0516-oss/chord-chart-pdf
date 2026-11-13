"""Chord shape library and fretboard diagram drawing."""
from __future__ import annotations

from .model import Chart, Shape
from .parser import ChartError
from .text import BOLD, REGULAR, pretty

_SHAPES = {
    "C": ("x32010", "-32-1-"), "A": ("x02220", "--123-"), "Am": ("x02210", "--231-"),
    "G": ("320003", "21---3"), "E": ("022100", "-231--"), "Em": ("022000", "-23---"),
    "D": ("xx0232", "---132"), "Dm": ("xx0231", "---231"), "F": ("133211", "134211"),
    "E7": ("020100", "-2-1--"), "A7": ("x02020", "--2-3-"), "D7": ("xx0212", "---213"),
    "G7": ("320001", "32---1"), "B7": ("x21202", "-213-4"), "C7": ("x32310", "-3241-"),
    "Am7": ("x02010", "--2-1-"), "Em7": ("020000", "-2----"), "Dm7": ("xx0211", "---211"),
    "Cmaj7": ("x32000", "-32---"), "Fmaj7": ("xx3210", "--321-"), "Bm": ("x24432", "-13421"),
    "G/B": ("x20033", "-1--34"), "D/F#": ("200232", "1--243"),
}
LIBRARY: dict[str, Shape] = {n: Shape(n, f, g) for n, (f, g) in _SHAPES.items()}
FRETS_SHOWN = 4


def shapes_for(chart: Chart) -> list[Shape]:
    shapes = list(chart.custom_shapes)
    covered = {s.name for s in shapes}
    for name in chart.diagram_names:
        if name in covered:
            continue
        if name not in LIBRARY:
            raise ChartError(
                f"no chord shape for '{name}': add a line like 'diagram {name}: x32010'")
        shapes.append(LIBRARY[name])
        covered.add(name)
    return shapes


def draw_diagram(canvas, shape: Shape, x: float, y: float, width: float) -> float:
    """Draw a diagram with its top-left corner at (x, y). Returns the height used."""
    frets = [None if ch == "x" else int(ch) for ch in shape.frets]
    fretted = [f for f in frets if f]
    base = min(fretted) if fretted and max(fretted) > FRETS_SHOWN else 1
    gap = width * 0.72 / 5
    fret_h = gap * 1.2
    left = x + (width - gap * 5) / 2
    name_size = width * 0.2
    top = y - name_size * 1.25 - gap * 0.95  # nut line

    canvas.saveState()
    canvas.setFillColorRGB(0, 0, 0)
    canvas.setStrokeColorRGB(0, 0, 0)
    canvas.setFont(BOLD, name_size)
    canvas.drawCentredString(x + width / 2, y - name_size, pretty(shape.name))

    canvas.setLineWidth(0.6)
    for i in range(6):
        canvas.line(left + i * gap, top, left + i * gap, top - fret_h * FRETS_SHOWN)
    for j in range(FRETS_SHOWN + 1):
        canvas.line(left, top - j * fret_h, left + 5 * gap, top - j * fret_h)
    if base == 1:
        canvas.setLineWidth(2.2)
        canvas.line(left - 0.3, top, left + 5 * gap + 0.3, top)
    else:
        canvas.setFont(REGULAR, gap * 0.85)
        canvas.drawRightString(left - gap * 0.5, top - fret_h * 0.5 - gap * 0.3, f"{base}fr")

    r = gap * 0.38
    mark_y = top + gap * 0.5
    for i, f in enumerate(frets):
        cx = left + i * gap
        if f is None:
            d = gap * 0.24
            canvas.setLineWidth(0.9)
            canvas.line(cx - d, mark_y - d, cx + d, mark_y + d)
            canvas.line(cx - d, mark_y + d, cx + d, mark_y - d)
        elif f == 0:
            canvas.setLineWidth(0.8)
            canvas.circle(cx, mark_y, gap * 0.26, stroke=1, fill=0)
        else:
            cy = top - (f - base + 0.5) * fret_h
            canvas.circle(cx, cy, r, stroke=0, fill=1)
            finger = shape.fingers[i] if shape.fingers else "-"
            if finger.isdigit():
                canvas.setFillColorRGB(1, 1, 1)
                canvas.setFont(BOLD, r * 1.35)
                canvas.drawCentredString(cx, cy - r * 0.48, finger)
                canvas.setFillColorRGB(0, 0, 0)
    canvas.restoreState()
    return (y - top) + fret_h * FRETS_SHOWN + gap * 0.4
