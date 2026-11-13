"""Draw a Chart as a letter-size PDF."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from .diagrams import draw_diagram, shapes_for
from .model import Bar, BarLine, Chart, Roadmap, ScaleDiagram, Section, Tab
from .neck import draw_scale, scale_height
from .notation import REST_W, draw_fermata, draw_rest, draw_rhythm, rhythm_events, rhythm_width
from .parser import ChartError
from .tab import column_width, draw_tab, tab_height
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
    if not re.fullmatch(r"[A-Za-z]\d*", label):
        return HexColor(OTHER_COLOR)
    return HexColor(LABEL_COLORS.get(label[0].upper(), OTHER_COLOR))


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
    w = _label_box_w(label, h, size)
    c.setFillColor(label_color(label))
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    c.rect(x, y_bottom, w, h, stroke=1, fill=1)
    c.setFillColor(black)
    c.setFont(BOLD, size)
    c.drawCentredString(x + w / 2, y_bottom + (h - size * 0.72) / 2, label)
    return w


STRUM_SCALE = 0.85


def _section_header(section: Section, first: bool) -> Block | None:
    if not (section.label or section.name or section.strum):
        return None
    gap = 0 if first else 12
    accents = bool(section.strum) and any(">" in t for t in section.strum)

    def draw(c: Canvas, y: float, s: float) -> None:
        bottom = y - gap * s - 18
        x = MARGIN
        if section.label:
            x += _draw_label_box(c, section.label, x, bottom, 18, 12) + 8
        if section.name:
            c.setFillColor(GREY)
            c.setFont(BOLD, 11)
            c.drawString(x, bottom + 5, section.name.upper())
            x += width(section.name.upper(), BOLD, 11) + 8
        c.setFillColor(black)
        c.setStrokeColor(black)
        if section.strum:
            x += 8
            x += draw_rhythm(c, section.strum, x, bottom + 2, STRUM_SCALE) + 4
        if section.strum_note:
            c.setFillColor(GREY)
            c.setFont(REGULAR, 9.5)
            c.drawString(x, bottom + 5, section.strum_note)
            c.setFillColor(black)

    return Block(20 + (5 if accents else 0), gap + 4, draw, keep_with_next=True)


# ---------- bar rows ----------

READABLE_SIZE = 12
SIMILE_W = 20


def _pads(bar: Bar) -> tuple[float, float]:
    return (20 if bar.repeat_start else 9), (15 if bar.repeat_end else 10 if bar.final else 4)


FERMATA = "(fermata)"
_REST_ITEM = re.compile(r"^r(16|8|4|2|1)\.?$")


def item_kind(item: str) -> str:
    if item == "%":
        return "simile"
    if _REST_ITEM.match(item):
        return "rest"
    if item.startswith("("):
        return "rhythm"
    return "chord"


def chord_name(item: str) -> str:
    return item[:-len(FERMATA)] if item.endswith(FERMATA) else item


def item_width(item: str, size: float) -> float:
    kind = item_kind(item)
    if kind == "simile":
        return SIMILE_W
    if kind == "rest":
        return REST_W
    if kind == "rhythm":
        return rhythm_width(item[1:-1].split())
    return width(pretty(chord_name(item)), BOLD, size)


ITEM_GAP = 8.0


def _chords_only(bar: Bar) -> bool:
    return all(item_kind(i) == "chord" for i in bar.chords)


def bar_need(bar: Bar, size: float) -> float:
    """Narrowest width at which this bar's contents clear its barlines."""
    left, right = _pads(bar)
    widths = [item_width(item, size) for item in bar.chords]
    if _chords_only(bar):        # equal slots, so two chords read as half a bar each
        gap = 6 if len(widths) > 1 else 2
        return left + right + len(widths) * (max(widths) + gap)
    return left + right + sum(widths) + ITEM_GAP * (len(widths) - 1) + 2


def item_positions(bar: Bar, left: float, right: float, size: float) -> list[float]:
    """Left x of each item between the bar's inner edges."""
    k = len(bar.chords)
    if _chords_only(bar):
        return [left + i * (right - left) / k for i in range(k)]
    widths = [item_width(item, size) for item in bar.chords]
    gap = min(28.0, (right - left - sum(widths)) / k)
    xs, x = [], left
    for w in widths:
        xs.append(x)
        x += w + gap
    return xs


@dataclass
class Row:
    bars: list[Bar]
    widths: list[float]
    size: float


def _fit_row(bars: list[Bar], per_line: int, min_size: float) -> Row | None:
    natural = CONTENT_W * len(bars) / max(per_line, len(bars))
    equal = natural / len(bars)
    size = float(CHORD_SIZE)
    while size >= min_size:
        needs = [bar_need(b, size) for b in bars]
        if max(needs) <= equal:
            return Row(bars, [equal] * len(bars), size)
        if sum(needs) <= CONTENT_W:
            spare = (CONTENT_W - sum(needs)) / len(bars)
            return Row(bars, [n + spare for n in needs], size)
        size -= 0.5
    return None


def _plan_chunk(bars: list[Bar], per_line: int) -> list[Row]:
    row = _fit_row(bars, per_line, READABLE_SIZE)
    if row:
        return [row]
    if len(bars) > 1:
        half = (len(bars) + 1) // 2
        return _plan_chunk(bars[:half], per_line) + _plan_chunk(bars[half:], per_line)
    row = _fit_row(bars, per_line, 1)
    if row is None:
        raise ChartError(f"bar '{' '.join(bars[0].chords)}' is too long to fit on the page")
    return [row]


def plan_rows(line: BarLine, per_line: int) -> list[Row]:
    bars = line.bars
    chunks = [bars] if len(bars) <= per_line + 2 else [
        bars[i:i + per_line] for i in range(0, len(bars), per_line)]
    return [row for chunk in chunks for row in _plan_chunk(chunk, per_line)]


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


def _bar_row(row: Row) -> Block:
    bars = row.bars
    extras = EXTRAS_H if any(
        b.ending or b.repeat_count or any(i.endswith(FERMATA) for i in b.chords) for b in bars) else 0
    edges = [MARGIN]
    for w in row.widths:
        edges.append(edges[-1] + w)

    def draw(c: Canvas, y: float, s: float) -> None:
        top = y - extras - 6 * s
        bottom = top - BAR_H
        baseline = bottom + 7
        c.setStrokeColor(black)
        c.setFillColor(black)
        for i, bar in enumerate(bars):
            x0, x1 = edges[i], edges[i + 1]
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
            pad_l, pad_r = _pads(bar)
            left, right = x0 + pad_l, x1 - pad_r
            slot = (right - left) / len(bar.chords)
            xs = item_positions(bar, left, right, row.size)
            for k, item in enumerate(bar.chords):
                sx = xs[k]
                kind = item_kind(item)
                if kind == "simile":
                    _draw_simile(c, sx + SIMILE_W / 2 if len(bar.chords) > 1 else (left + right) / 2, baseline)
                elif kind == "rest":
                    draw_rest(c, int(_REST_ITEM.match(item).group(1)), sx, baseline)
                elif kind == "rhythm":
                    draw_rhythm(c, item[1:-1].split(), sx, baseline + 1)
                else:
                    name = pretty(chord_name(item))
                    size = fitted_font_size([chord_name(item)], slot - 1, row.size)
                    c.setFont(BOLD, size)
                    c.drawString(sx, baseline, name)
                    if item.endswith(FERMATA):
                        draw_fermata(c, sx + width(name, BOLD, size) / 2, baseline + size * 0.93)
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
                bx1 = edges[j + 1] - 3
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

Run = tuple[str, str]          # ("arrow", "") | ("label", "A1") | ("text", "words")
ROADMAP_INDENT = 2
ROADMAP_LINE_H = 16


def _label_box_w(label: str, h: float, size: float) -> float:
    return max(h + 4, width(label, BOLD, size) + 10)


def _run_width(run: Run) -> float:
    kind, value = run
    if kind == "arrow":
        return width(ARROW, BOLD, 13) + 7
    if kind == "label":
        return _label_box_w(value, 16, 10.5) + 7
    return width(value, REGULAR, 11) + 7


def runs_width(line: list[Run]) -> float:
    return ROADMAP_INDENT + sum(_run_width(r) for r in line)


def roadmap_lines(item: Roadmap, labels: set[str]) -> list[list[Run]]:
    """Split a roadmap note into lines that fit the page width."""
    atoms: list[Run] = [("arrow", "")]
    toks = item.text.split()
    i = 0
    while i < len(toks):
        if toks[i] == "->":
            atoms.append(("arrow", ""))
            i += 1
            continue
        for j in range(len(toks), i, -1):          # longest label first: "CHORUS 2" before "CHORUS"
            if " ".join(toks[i:j]) in labels:
                atoms.append(("label", " ".join(toks[i:j])))
                i = j
                break
        else:
            atoms.append(("text", toks[i]))
            i += 1
    lines: list[list[Run]] = [[]]
    for atom in atoms:
        line = lines[-1]
        merged = line[:-1] + [("text", line[-1][1] + " " + atom[1])] \
            if atom[0] == "text" and line and line[-1][0] == "text" else line + [atom]
        if line and runs_width(merged) > CONTENT_W:
            lines.append([atom])
        else:
            lines[-1] = merged
    return lines


def _roadmap(item: Roadmap, labels: set[str]) -> Block:
    lines = roadmap_lines(item, labels)

    def draw(c: Canvas, y: float, s: float) -> None:
        c.setFillColor(black)
        for n, runs in enumerate(lines):
            bottom = y - 3 * s - 16 - n * ROADMAP_LINE_H * 1.15
            x = MARGIN + ROADMAP_INDENT
            for kind, value in runs:
                if kind == "arrow":
                    c.setFont(BOLD, 13)
                    c.drawString(x, bottom + 3.5, ARROW)
                elif kind == "label":
                    _draw_label_box(c, value, x, bottom, 16, 10.5)
                else:
                    c.setFont(REGULAR, 11)
                    c.drawString(x, bottom + 4, value)
                x += _run_width((kind, value))

    return Block(18 + (len(lines) - 1) * ROADMAP_LINE_H * 1.15, 8, draw)


# ---------- header ----------

TITLE_SIZE = 24.0
ARTIST_SIZE = 13.0
MIN_HEADER_TITLE = 18.0   # below this, diagrams leave the header band


@dataclass
class HeaderPlan:
    diagrams_in_header: bool
    right: float          # right edge available to capo/title/artist
    title_size: float
    title_width: float
    artist_size: float


def _shrink(text: str | None, font: str, size: float, avail: float, floor: float = 1.0) -> float:
    while text and size > floor and width(text, font, size) > avail:
        size -= 0.5
    return size


def header_plan(chart: Chart, shapes) -> HeaderPlan:
    capo_w = width(f"Capo {chart.capo}", BOLD, 15) + 16 if chart.capo is not None else 0.0
    full_right = PAGE_W - MARGIN

    def plan(in_header: bool, right: float) -> HeaderPlan:
        title_w = right - capo_w - MARGIN
        return HeaderPlan(in_header, right,
                          _shrink(chart.title, BOLD, TITLE_SIZE, title_w), title_w,
                          _shrink(chart.artist, REGULAR, ARTIST_SIZE, right - MARGIN))

    strip = len(shapes) * (DIAGRAM_W + DIAGRAM_GAP) - DIAGRAM_GAP
    if shapes and strip + DIAGRAM_GAP <= CONTENT_W * 0.5:
        p = plan(True, full_right - strip - 18)
        if p.title_size >= MIN_HEADER_TITLE and p.artist_size >= ARTIST_SIZE:
            return p
    return plan(False, full_right)


def _draw_header(c: Canvas, chart: Chart, shapes) -> float:
    """Draw title block and chord diagrams. Returns the y where content starts."""
    top = PAGE_H - MARGIN
    if not (chart.title or chart.artist or chart.capo is not None or shapes):
        return top
    hp = header_plan(chart, shapes)
    diagram_h = 0.0
    if hp.diagrams_in_header:
        x = hp.right + 18
        for i, shape in enumerate(shapes):
            diagram_h = draw_diagram(c, shape, x + i * (DIAGRAM_W + DIAGRAM_GAP), top, DIAGRAM_W)
    if chart.capo is not None:
        c.setFillColor(CAPO_GREEN)
        c.setFont(BOLD, 15)
        c.drawRightString(hp.right, top - 21, f"Capo {chart.capo}")
    c.setFillColor(black)
    text_h = 0.0
    if chart.title:
        c.setFont(BOLD, hp.title_size)
        c.drawString(MARGIN, top - 22, chart.title)
        text_h = 28
    if chart.artist:
        c.setFillColor(GREY)
        c.setFont(REGULAR, hp.artist_size)
        c.drawString(MARGIN, top - text_h - 14, chart.artist)
        c.setFillColor(black)
        text_h += 20
    if chart.capo is not None:
        text_h = max(text_h, 26)
    y = top - max(text_h, diagram_h) - 8
    if shapes and not hp.diagrams_in_header:
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

def _scale_block(item: ScaleDiagram) -> Block:
    return Block(scale_height() + 4, 8, lambda c, y, s: draw_scale(c, item, MARGIN, y - 4 * s, CONTENT_W))


def _tab_block(item: Tab) -> Block:
    if column_width(item, CONTENT_W) is None:
        raise ChartError("tab is too wide for the page; split it into two 'tab:' blocks")
    return Block(tab_height(item) + 2, 8, lambda c, y, s: draw_tab(c, item, MARGIN, y - 4 * s, CONTENT_W))


def _blocks(chart: Chart) -> list[Block]:
    labels = {s.label for s in chart.sections if s.label}
    blocks: list[Block] = []
    for section in chart.sections:
        header = _section_header(section, first=not blocks)
        if header:
            blocks.append(header)
        for item in section.items:
            if isinstance(item, Roadmap):
                blocks.append(_roadmap(item, labels))
            elif isinstance(item, ScaleDiagram):
                blocks.append(_scale_block(item))
            elif isinstance(item, Tab):
                blocks.append(_tab_block(item))
            else:
                blocks.extend(_bar_row(row) for row in plan_rows(item, chart.bars_per_line))
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
