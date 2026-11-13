"""Rhythm slashes, rests and fermatas."""
from __future__ import annotations

from dataclasses import dataclass

from .parser import RHYTHM_TOKEN

ADVANCE = {16: 8.5, 8: 11.0, 4: 15.0, 2: 22.0, 1: 28.0}   # points per event at scale 1
REST_W = 9.0
HEAD = 5.0
STEM_TOP = 17.0


@dataclass
class Event:
    dur: int
    rest: bool
    dotted: bool
    accent: bool
    beam: int | None = None     # index of the beam group, None when unbeamed
    x: float = 0.0              # left edge at scale 1


def rhythm_events(tokens: list[str]) -> list[Event]:
    events: list[Event] = []
    pos = 0.0                   # position in sixteenths
    x = 0.0
    group = -1
    prev_beat: int | None = None
    for tok in tokens:
        m = RHYTHM_TOKEN.match(tok)
        ev = Event(int(m.group(2)), bool(m.group(1)), bool(m.group(3)), bool(m.group(4)), x=x)
        beat = int(pos // 4)
        beamable = not ev.rest and ev.dur >= 8
        prev = events[-1] if events else None
        if beamable and prev is not None and not prev.rest and prev.dur >= 8 and prev_beat == beat:
            if prev.beam is None:
                group += 1
                prev.beam = group
            ev.beam = prev.beam
        events.append(ev)
        prev_beat = beat
        pos += 16 / ev.dur * (1.5 if ev.dotted else 1)
        x += ADVANCE[ev.dur] * (1.3 if ev.dotted else 1)
    return events


def rhythm_width(tokens: list[str], k: float = 1.0) -> float:
    return sum(ADVANCE[e.dur] * (1.3 if e.dotted else 1) for e in rhythm_events(tokens)) * k


REST_DOT_W = 4.0


def draw_rest(c, dur: int, x: float, y: float, k: float = 1.0, dotted: bool = False) -> None:
    """Draw a rest with its left edge at x; y is the text baseline."""
    c.saveState()
    if dotted:
        dot_x = x + (11.5 if dur in (1, 2) else 8.5) * k
        c.circle(dot_x, y + (9 if dur in (1, 2) else 8.5) * k, 1.1 * k, stroke=0, fill=1)
    c.setLineCap(1)
    c.setLineJoin(1)
    if dur == 4:
        c.setLineWidth(1.7 * k)
        p = c.beginPath()
        pts = [(1.5, 15), (5, 10.5), (2, 7.5), (5.2, 4)]
        p.moveTo(x + pts[0][0] * k, y + pts[0][1] * k)
        for px, py in pts[1:]:
            p.lineTo(x + px * k, y + py * k)
        p.curveTo(x + 1.5 * k, y + 5.2 * k, x + 1.2 * k, y + 2.2 * k, x + 3.6 * k, y + 0.8 * k)
        c.drawPath(p, stroke=1, fill=0)
    elif dur in (1, 2):
        line_y = y + (11 if dur == 1 else 7) * k
        c.setLineWidth(0.9 * k)
        c.line(x - 2 * k, line_y, x + 11 * k, line_y)
        c.rect(x, line_y - (4 * k if dur == 1 else 0), 9 * k, 4 * k, stroke=0, fill=1)
    else:
        c.setLineWidth(1.2 * k)
        for n in range(2 if dur == 16 else 1):
            c.circle(x + (1.6 - 0.7 * n) * k, y + (10 - 4 * n) * k, 1.5 * k, stroke=0, fill=1)
            c.line(x + (2.4 - 0.7 * n) * k, y + (9.6 - 4 * n) * k, x + (5.4 - 0.5 * n) * k, y + (11 - 4 * n) * k)
        c.line(x + 5.4 * k, y + 11 * k, x + 2.8 * k, y + 1 * k)
    c.restoreState()


def draw_rhythm(c, tokens: list[str], x: float, y: float, k: float = 1.0) -> float:
    """Draw rhythm slashes starting at x with noteheads sitting on y. Returns the width."""
    events = rhythm_events(tokens)
    c.saveState()
    c.setLineCap(1)
    stems: dict[int, list[tuple[float, int]]] = {}
    for e in events:
        px = x + e.x * k
        if e.rest:
            draw_rest(c, e.dur, px, y, k, e.dotted)
            continue
        if e.dur >= 4:
            c.setLineWidth(2.3 * k)
            c.line(px + 0.6 * k, y + 0.6 * k, px + (HEAD - 0.6) * k, y + (HEAD - 0.6) * k)
        else:
            c.setLineWidth(1.1 * k)
            p = c.beginPath()
            p.moveTo(px, y + HEAD * k / 2)
            p.lineTo(px + HEAD * k / 2, y + HEAD * k)
            p.lineTo(px + HEAD * k, y + HEAD * k / 2)
            p.lineTo(px + HEAD * k / 2, y)
            p.close()
            c.drawPath(p, stroke=1, fill=0)
        if e.dotted:
            c.circle(px + (HEAD + 2.5) * k, y + 1.5 * k, 0.9 * k, stroke=0, fill=1)
        sx = px + HEAD * k
        if e.dur >= 2:
            c.setLineWidth(0.95 * k)
            c.line(sx, y + (HEAD - 0.8) * k, sx, y + STEM_TOP * k)
        if e.beam is not None:
            stems.setdefault(e.beam, []).append((sx, e.dur))
        elif e.dur >= 8:
            c.setLineWidth(1.3 * k)
            for n in range(2 if e.dur == 16 else 1):
                c.line(sx, y + (STEM_TOP - 3.5 * n) * k, sx + 4 * k, y + (STEM_TOP - 5 - 3.5 * n) * k)
        if e.accent:
            c.setLineWidth(0.95 * k)
            c.line(px - 0.3 * k, y - 2.3 * k, px + 5.6 * k, y - 4.3 * k)
            c.line(px + 5.6 * k, y - 4.3 * k, px - 0.3 * k, y - 6.3 * k)
    c.setLineCap(0)
    for group in stems.values():
        c.setLineWidth(2.4 * k)
        c.line(group[0][0] - 0.45 * k, y + (STEM_TOP - 1.2) * k, group[-1][0] + 0.45 * k, y + (STEM_TOP - 1.2) * k)
        run: list[float] = []
        for sx, dur in group + [(0.0, 0)]:
            if dur == 16:
                run.append(sx)
            else:
                if len(run) > 1:
                    c.line(run[0] - 0.45 * k, y + (STEM_TOP - 5) * k, run[-1] + 0.45 * k, y + (STEM_TOP - 5) * k)
                elif len(run) == 1:
                    c.line(run[0] - 3.5 * k, y + (STEM_TOP - 5) * k, run[0], y + (STEM_TOP - 5) * k)
                run = []
    c.restoreState()
    return rhythm_width(tokens, k)


def draw_fermata(c, cx: float, y: float) -> None:
    """Fermata centred on cx with its base at y."""
    c.saveState()
    c.setLineWidth(1.4)
    c.arc(cx - 6.5, y - 6.5, cx + 6.5, y + 6.5, 0, 180)
    c.circle(cx, y + 1.6, 1.4, stroke=0, fill=1)
    c.restoreState()
