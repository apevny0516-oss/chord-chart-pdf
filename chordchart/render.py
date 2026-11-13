"""Draw a Chart as a letter-size PDF."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from .diagrams import draw_diagram, shapes_for
from .model import Bar, BarLine, Chart, Roadmap, Section
from .text import ARROW, BOLD, REGULAR, pretty, width

PAGE_W, PAGE_H = letter
MARGIN = 0.6 * 72
CONTENT_W = PAGE_W - 2 * MARGIN

LABEL_COLORS = {"A": "#FFF27A", "B": "#7DF3FF", "C": "#FF8AF3", "D": "#A8F08A"}
OTHER_COLOR = "#DDDDDD"
CAPO_GREEN = HexColor("#5BB12F")
GREY = HexColor("#444444")

CHORD_SIZE = 20
MIN_CHORD_SIZE = 7
BAR_H = 28          # height of a barline
EXTRAS_H = 13       # room above a row for "x4" and ending brackets
DIAGRAM_W = 56
DIAGRAM_GAP = 6
MIN_SCALE = 0.2


def label_color(label: str) -> HexColor:
    return HexColor(LABEL_COLORS.get(label[:1].upper(), OTHER_COLOR))


def fitted_font_size(chords: list[str], slot_width: float, base: float = CHORD_SIZE) -> float:
    """Largest size up to `base` at which every chord fits in `slot_width`."""
    size = base
    while size > MIN_CHORD_SIZE and max(width(pretty(c), BOLD, size) for c in chords) > slot_width:
        size -= 0.5
    return size


@dataclass
class Block:
    fixed: float                      # height that never shrinks
    flex: float                       # spacing that shrinks to fit a page
    draw: Callable[[Canvas, float, float], None]   # (canvas, y_top, scale)
    keep_with_next: bool = False

    def height(self, scale: float) -> float:
        return self.fixed + self.flex * scale


# ---------- section header ----------

def _draw_label_box(c: Canvas, label: str, x: float, y_bottom: float, h: float, size: float) -> float:
    w = max(h + 4, width(label, BOLD, size) + 10)
    c.setFillColor(label_color(label))
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    c.rect(x, y_bottom, w, h, stroke=1, fill=1)
    c.setFillColor(black)
    c.setFont(BOLD, size)
    c.drawCentredString(x + w / 2, y_bottom + (h - size * 0.72) / 2, label)
    return w


def _section_header(section: Section, first: bool) -> Block:
    gap = 0 if first else 12

    def draw(c: Canvas, y: float, s: float) -> None:
        bottom = y - gap * s - 18
        w = _draw_label_box(c, section.label, MARGIN, bottom, 18, 12)
        if section.name:
            c.setFillColor(GREY)
            c.setFont(BOLD, 11)
            c.drawString(MARGIN + w + 8, bottom + 5, section.name.upper())
            c.setFillColor(black)

    return Block(20, gap + 4, draw, keep_with_next=True)


# ---------- bar rows ----------

def _rows(line: BarLine, per_line: int) -> list[list[Bar]]:
    bars = line.bars
    if len(bars) <= per_line + 2:
        return [bars]
    return [bars[i:i + per_line] for i in range(0, len(bars), per_line)]


def _thin(c: Canvas, x: float, y0: float, y1: float) -> None:
    c.setLineWidth(1.1)
    c.line(x, y0, x, y1)


def _thick(c: Canvas, x: float, y0: float, y1: float) -> None:
    c.setLineWidth(3)
    c.line(x, y0, x, y1)


def _dots(c: Canvas, x: float, y0: float, y1: float) -> None:
    mid = (y0 + y1) / 2
    for dy in (-4.5, 4.5):
        c.circle(x, mid + dy, 1.7, stroke=0, fill=1)


def _draw_simile(c: Canvas, cx: float, baseline: float) -> None:
    c.setLineWidth(2.8)
    c.line(cx - 7, baseline + 0.5, cx + 7, baseline + 14)
    c.circle(cx - 6, baseline + 11.5, 1.9, stroke=0, fill=1)
    c.circle(cx + 6, baseline + 3, 1.9, stroke=0, fill=1)


def _bar_row(bars: list[Bar], per_line: int) -> Block:
    extras = EXTRAS_H if any(b.ending or b.repeat_count for b in bars) else 0
    bar_w = CONTENT_W / max(per_line, len(bars))

    def draw(c: Canvas, y: float, s: float) -> None:
        top = y - extras - 6 * s
        bottom = top - BAR_H
        baseline = bottom + 7
        c.setStrokeColor(black)
        c.setFillColor(black)
        for i, bar in enumerate(bars):
            x0 = MARGIN + i * bar_w
            x1 = x0 + bar_w
            # left edge
            if bar.repeat_start:
                _thick(c, x0 + 1.5, bottom, top)
                _thin(c, x0 + 6, bottom, top)
                _dots(c, x0 + 10.5, bottom, top)
            elif i == 0:
                _thin(c, x0, bottom, top)
            # right edge
            if bar.repeat_end:
                _thick(c, x1 - 1.5, bottom, top)
                _thin(c, x1 - 6, bottom, top)
                _dots(c, x1 - 10.5, bottom, top)
            elif bar.final:
                _thick(c, x1 - 1.5, bottom, top)
                _thin(c, x1 - 6, bottom, top)
            elif not (i + 1 < len(bars) and bars[i + 1].repeat_start):
                _thin(c, x1, bottom, top)
            # chords
            left = x0 + (20 if bar.repeat_start else 9)
            right = x1 - (15 if bar.repeat_end else 10 if bar.final else 4)
            if bar.chords == ["%"]:
                _draw_simile(c, (left + right) / 2, baseline)
            else:
                slot = (right - left) / len(bar.chords)
                size = fitted_font_size(bar.chords, slot - 4)
                c.setFont(BOLD, size)
                for k, chord in enumerate(bar.chords):
                    c.drawString(left + k * slot, baseline, pretty(chord))
            # repeat count
            count_w = 0.0
            if bar.repeat_count:
                label = f"x{bar.repeat_count}"
                c.setFont(BOLD, 10)
                count_w = width(label, BOLD, 10) + 6
                c.drawRightString(x1 - 1, top + 3.5, label)
            # ending bracket: one per run of bars sharing an ending
            if bar.ending and (i == 0 or bars[i - 1].ending != bar.ending):
                j = i
                while j + 1 < len(bars) and bars[j + 1].ending == bar.ending:
                    j += 1
                last = bars[j]
                bx0 = x0 + 3
                bx1 = MARGIN + (j + 1) * bar_w - 3
                if last.repeat_count:
                    bx1 -= width(f"x{last.repeat_count}", BOLD, 10) + 6
                by = top + 10.5
                c.setLineWidth(1.1)
                c.line(bx0, by - 8, bx0, by)
                c.line(bx0, by, bx1, by)
                if last.final:
                    c.line(bx1, by, bx1, by - 8)
                c.setFont(BOLD, 8.5)
                c.drawString(bx0 + 4, by - 8.5, ", ".join(str(n) for n in bar.ending) + ".")

    return Block(BAR_H + 6 + extras, 12, draw)


# ---------- roadmap ----------

def _roadmap(item: Roadmap, labels: set[str]) -> Block:
    runs: list[tuple[str, str]] = [("arrow", "")]
    for tok in item.text.split():
        if tok == "->":
            runs.append(("arrow", ""))
        elif tok in labels:
            runs.append(("label", tok))
        elif runs and runs[-1][0] == "text":
            runs[-1] = ("text", runs[-1][1] + " " + tok)
        else:
            runs.append(("text", tok))

    def draw(c: Canvas, y: float, s: float) -> None:
        bottom = y - 3 * s - 16
        x = MARGIN + 2
        c.setFillColor(black)
        for kind, value in runs:
            if kind == "arrow":
                c.setFont(BOLD, 13)
                c.drawString(x, bottom + 3.5, ARROW)
                x += width(ARROW, BOLD, 13) + 7
            elif kind == "label":
                x += _draw_label_box(c, value, x, bottom, 16, 10.5) + 7
            else:
                c.setFont(REGULAR, 11)
                c.drawString(x, bottom + 4, value)
                x += width(value, REGULAR, 11) + 7

    return Block(18, 8, draw)


# ---------- header ----------

def _draw_header(c: Canvas, chart: Chart, shapes) -> float:
    """Draw title block and chord diagrams. Returns the y where content starts."""
    top = PAGE_H - MARGIN
    if not (chart.title or chart.artist or chart.capo is not None or shapes):
        return top
    right = PAGE_W - MARGIN
    diagram_h = 0.0
    in_header = shapes and len(shapes) * (DIAGRAM_W + DIAGRAM_GAP) <= CONTENT_W * 0.5
    if in_header:
        x = right - len(shapes) * DIAGRAM_W - (len(shapes) - 1) * DIAGRAM_GAP
        for i, shape in enumerate(shapes):
            diagram_h = draw_diagram(c, shape, x + i * (DIAGRAM_W + DIAGRAM_GAP), top, DIAGRAM_W)
        right = x - 18
    capo_w = 0.0
    if chart.capo is not None:
        label = f"Capo {chart.capo}"
        c.setFillColor(CAPO_GREEN)
        c.setFont(BOLD, 15)
        c.drawRightString(right, top - 21, label)
        capo_w = width(label, BOLD, 15) + 16
    c.setFillColor(black)
    text_h = 0.0
    if chart.title:
        avail = right - capo_w - MARGIN
        size = 24.0
        while size > 12 and width(chart.title, BOLD, size) > avail:
            size -= 1
        c.setFont(BOLD, size)
        c.drawString(MARGIN, top - 22, chart.title)
        text_h = 28
    if chart.artist:
        c.setFillColor(GREY)
        c.setFont(REGULAR, 13)
        c.drawString(MARGIN, top - text_h - 14, chart.artist)
        c.setFillColor(black)
        text_h += 20
    if chart.capo is not None:
        text_h = max(text_h, 26)
    y = top - max(text_h, diagram_h) - 8
    if shapes and not in_header:
        per_row = int((CONTENT_W + DIAGRAM_GAP) // (DIAGRAM_W + DIAGRAM_GAP))
        for start in range(0, len(shapes), per_row):
            h = 0.0
            for i, shape in enumerate(shapes[start:start + per_row]):
                h = draw_diagram(c, shape, MARGIN + i * (DIAGRAM_W + DIAGRAM_GAP), y, DIAGRAM_W)
            y -= h + 8
    c.setStrokeColor(HexColor("#BBBBBB"))
    c.setLineWidth(0.75)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    c.setStrokeColor(black)
    return y - 12


def _draw_footer(c: Canvas, chart: Chart) -> None:
    if chart.footer:
        c.setFillColor(GREY)
        c.setFont(REGULAR, 9)
        c.drawCentredString(PAGE_W / 2, MARGIN - 4, chart.footer)
        c.setFillColor(black)


# ---------- top level ----------

def _blocks(chart: Chart) -> list[Block]:
    labels = {s.label for s in chart.sections}
    blocks: list[Block] = []
    for n, section in enumerate(chart.sections):
        blocks.append(_section_header(section, first=(n == 0)))
        for item in section.items:
            if isinstance(item, Roadmap):
                blocks.append(_roadmap(item, labels))
            else:
                blocks.extend(_bar_row(row, chart.bars_per_line)
                              for row in _rows(item, chart.bars_per_line))
    return blocks


def render(chart: Chart, out_path: str) -> None:
    shapes = shapes_for(chart)
    blocks = _blocks(chart)
    c = Canvas(out_path, pagesize=letter)
    c.setTitle(chart.title or "Chord chart")
    if chart.artist:
        c.setAuthor(chart.artist)
    bottom = MARGIN + (12 if chart.footer else 0)
    y = _draw_header(c, chart, shapes)
    _draw_footer(c, chart)

    # Tighten spacing so a chart that nearly fits one page does fit.
    fixed = sum(b.fixed for b in blocks)
    flex = sum(b.flex for b in blocks)
    scale = 1.0
    if fixed + flex > y - bottom and flex > 0:
        fit = (y - bottom - fixed) / flex
        if fit >= MIN_SCALE:
            scale = fit

    for i, block in enumerate(blocks):
        need = block.height(scale)
        if block.keep_with_next and i + 1 < len(blocks):
            need += blocks[i + 1].height(scale)
        if y - need < bottom - 0.01:
            c.showPage()
            _draw_footer(c, chart)
            y = PAGE_H - MARGIN
        block.draw(c, y, scale)
        y -= block.height(scale)
    c.save()
