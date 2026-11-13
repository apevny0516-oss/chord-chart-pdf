"""Parse the plain-text chart format into a Chart."""
from __future__ import annotations

import re

from .model import Bar, BarLine, Chart, Roadmap, Section, Shape


class ChartError(ValueError):
    pass


HEADER_KEYS = {"title", "artist", "capo", "footer", "bars_per_line"}
_TOKEN = re.compile(r"\s*(\|\|:|:\|\||\|\||\||\{[\d,\s]+:|\}|[^\s|{}:]+)")
_SECTION = re.compile(r"^\[([^\]]+)\]\s*(.*)$")
_DIAGRAM = re.compile(r"^diagram\s+(\S+)\s*:\s*(.*)$")
_HEADER = re.compile(r"^(\w+)\s*:\s*(.*)$")
_COUNT = r"\(?\s*(?:[xX]\s*(\d+)|(\d+)\s*[xX])\s*\)?"
_COUNT_AFTER_REPEAT = re.compile(r":\|\|\s*" + _COUNT)
_COUNT_ONLY = re.compile(r"^" + _COUNT + r"$")
_CHORD = re.compile(
    r"^[A-G][#b]?"
    r"(?:maj|min|dim|aug|sus|add|omit|no|alt|M|m|\u00b0|\u00f8|\u0394|\+|-|[#b]?\d+|\(|\)|,|/\d+)*"
    r"(?:/[A-G][#b]?)?$")
_NO_CHORD = {"%", "N.C.", "NC", "N.C"}


def _is_chord(tok: str) -> bool:
    return tok in _NO_CHORD or bool(_CHORD.match(tok))


def _err(n: int, msg: str) -> ChartError:
    return ChartError(f"line {n}: {msg}")


def _positive_int(n: int, key: str, value: str) -> int:
    if not value.isdigit():
        raise _err(n, f"{key} must be a whole number, got '{value}'")
    return int(value)


def _parse_diagram(n: int, name: str, rest: str) -> Shape:
    parts = rest.split()
    if not 1 <= len(parts) <= 2:
        raise _err(n, "diagram needs frets and optional fingers, e.g. 'diagram G/B: x20033 x2--34'")
    frets = parts[0].lower()
    if not re.fullmatch(r"[x0-9]{6}", frets):
        raise _err(n, f"frets '{parts[0]}' must be 6 characters of x or 0-9, low E string first")
    fingers = parts[1] if len(parts) == 2 else None
    if fingers is not None and not re.fullmatch(r"[-x1-4]{6}", fingers):
        raise _err(n, f"fingers '{fingers}' must be 6 characters of -, x or 1-4")
    return Shape(name, frets, fingers)


def _parse_bars(n: int, line: str, repeat_open: bool) -> tuple[list[Bar], bool]:
    line = line.replace("\u266f", "#").replace("\u266d", "b")
    line = _COUNT_AFTER_REPEAT.sub(lambda m: f":|| x{m.group(1) or m.group(2)}", line)
    bars: list[Bar] = []
    chords: list[str] = []
    ending_first_bar = 0
    ending_just_closed = False
    start_pending = False
    ending: tuple[int, ...] | None = None
    pending_ending: tuple[int, ...] | None = None

    def flush() -> None:
        nonlocal chords, start_pending, pending_ending, ending_just_closed
        if chords:
            bars.append(Bar(chords, repeat_start=start_pending, ending=pending_ending))
            chords, start_pending, pending_ending = [], False, None
        ending_just_closed = False

    pos = 0
    while pos < len(line):
        m = _TOKEN.match(line, pos)
        if not m:
            if not line[pos:].strip():
                break
            raise _err(n, f"can't read '{line[pos:].strip()}'")
        tok, pos = m.group(1), m.end()
        if tok == "||:":
            flush()
            if repeat_open:
                raise _err(n, "'||:' opens a repeat while another is still open")
            start_pending, repeat_open = True, True
        elif tok in (":||", "||"):
            flush()
            if not bars:
                raise _err(n, f"'{tok}' has no bar before it")
            if tok == ":||":
                if not repeat_open:
                    raise _err(n, "':||' closes a repeat that was never opened with '||:'")
                bars[-1].repeat_end, repeat_open = True, False
            else:
                bars[-1].final = True
        elif tok == "|":
            flush()
        elif tok.startswith("{"):
            flush()
            if ending is not None:
                raise _err(n, "'{' opened inside another ending")
            nums = [p.strip() for p in tok[1:-1].split(",")]
            if not all(p.isdigit() for p in nums):
                raise _err(n, f"ending numbers '{tok[1:-1]}' must look like 1,2,3")
            ending = tuple(int(p) for p in nums)
            ending_first_bar = len(bars)
        elif tok == "}":
            if ending is None:
                raise _err(n, "'}' without a matching '{'")
            if not chords and len(bars) == ending_first_bar:
                raise _err(n, "ending '{...}' has no bars inside it")
            ending_just_closed = bool(chords)
            ending = None
        elif re.fullmatch(r"x\d+", tok) and not chords and bars and bars[-1].repeat_end:
            bars[-1].repeat_count = int(tok[1:])
        elif not _is_chord(tok):
            raise _err(n, f"'{tok}' isn't a chord (notes and directions go on a line starting with '->')")
        elif ending_just_closed:
            raise _err(n, f"'{tok}' comes right after '}}' in the same bar; put a '|' after the '}}'")
        else:
            chords.append(tok)
            pending_ending = ending
    if ending is not None:
        raise _err(n, "ending '{' is never closed with '}'")
    if start_pending and not chords:
        raise _err(n, "'||:' has no bar after it")
    flush()
    if not bars:
        raise _err(n, "no bars found")
    return bars, repeat_open


def parse(text: str) -> Chart:
    chart = Chart()
    section: Section | None = None
    repeat_open = False
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if section is not None:
            line = line.replace("\u2192", "->").replace("\u00d7", "x")
        m = _DIAGRAM.match(line)
        if m:
            chart.custom_shapes.append(_parse_diagram(n, m.group(1), m.group(2)))
            continue
        if line.startswith("diagrams:"):
            names = [p.strip() for p in line[len("diagrams:"):].split(",") if p.strip()]
            if not names:
                raise _err(n, "'diagrams:' lists no chords")
            chart.diagram_names.extend(names)
            continue
        m = _SECTION.match(line)
        if m:
            section = Section(m.group(1).strip(), m.group(2).strip())
            chart.sections.append(section)
            repeat_open = False
            continue
        if section is None:
            m = _HEADER.match(line)
            if not m:
                raise _err(n, "bars must come after a section line like '[A] Verse'")
            key, value = m.group(1), m.group(2).strip()
            if key not in HEADER_KEYS:
                raise _err(n, f"unknown header '{key}' (known: {', '.join(sorted(HEADER_KEYS))})")
            if key in ("capo", "bars_per_line"):
                num = _positive_int(n, key, value)
                if key == "bars_per_line" and num < 1:
                    raise _err(n, "bars_per_line must be at least 1")
                setattr(chart, key, num)
            else:
                setattr(chart, key, value or None)
            continue
        if line.startswith("->"):
            section.items.append(Roadmap(line[2:].strip()))
            continue
        m = _COUNT_ONLY.match(line)
        if m:
            prev = section.items[-1] if section.items else None
            if not isinstance(prev, BarLine) or not prev.bars[-1].repeat_end:
                raise _err(n, f"'{line}' has no ':||' repeat before it to count")
            prev.bars[-1].repeat_count = int(m.group(1) or m.group(2))
            continue
        bars, repeat_open = _parse_bars(n, line, repeat_open)
        section.items.append(BarLine(bars))
    if not chart.sections:
        raise _err(max(1, len(text.splitlines())), "chart has no sections")
    return chart
