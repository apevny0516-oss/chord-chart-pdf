"""Parse the plain-text chart format into a Chart."""
from __future__ import annotations

import re

from .model import Bar, BarLine, Chart, Roadmap, ScaleDiagram, Section, Shape, Tab


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
RHYTHM_TOKEN = re.compile(r"^(r)?(16|8|4|2|1)(\.)?(>)?$")
_REST = re.compile(r"^r(16|8|4|2|1)\.?$")
_GROUP = re.compile(r"\(([^()|{}]*)\)")
_FERMATA = "(fermata)"
_STRUM = re.compile(r"^strum\s*:\s*(.*)$")
_SCALE = re.compile(r"^scale\s+([^:]+?)\s*:\s*(.*)$")
_TAB_STRING = re.compile(r"^[A-Ga-g]?[#b]?\|[-0-9|:hpbsxr/\\~()<>^. ]*-[-0-9|:hpbsxr/\\~()<>^. ]*$")


def is_rhythm_token(tok: str) -> bool:
    m = RHYTHM_TOKEN.match(tok)
    return bool(m) and not (m.group(1) and m.group(4))


def _canonical_item(tok: str) -> str | None:
    """Return the stored form of a bar item, or None if it isn't one."""
    if tok in _NO_CHORD or _REST.match(tok):
        return tok
    if tok.startswith("(") and tok.endswith(")"):
        parts = tok[1:-1].split("_")
        if parts and all(is_rhythm_token(p) for p in parts):
            return "(" + " ".join(parts) + ")"
        return None
    if tok.lower().endswith(_FERMATA):
        base = tok[:-len(_FERMATA)]
        return base + _FERMATA if _CHORD.match(base) else None
    return tok if _CHORD.match(tok) else None


def _join_group(m: re.Match) -> str:
    parts = m.group(1).split()
    if parts and all(is_rhythm_token(p) for p in parts):
        return "(" + "_".join(parts) + ")"
    return m.group(0)


def _parse_strum(n: int, rest: str) -> tuple[list[str], str | None]:
    note = None
    m = re.search(r'"([^"]*)"\s*$', rest)
    if m:
        note, rest = m.group(1).strip() or None, rest[:m.start()]
    tokens = rest.split()
    if not tokens:
        raise _err(n, "strum needs a rhythm, e.g. 'strum: 8> 8 8 8> 8 8 8> 8'")
    for tok in tokens:
        if not is_rhythm_token(tok):
            raise _err(n, f"'{tok}' isn't a rhythm value (use 1 2 4 8 16, '.' dotted, '>' accent, 'r' rest; notes go in quotes)")
    return tokens, note


def _parse_scale(n: int, name: str, rest: str) -> ScaleDiagram:
    dots: dict[int, list[int]] = {}
    first = last = None
    m = re.search(r"\bfrets\s+(\d+)\s*-\s*(\d+)", rest)
    if m:
        first, last = int(m.group(1)), int(m.group(2))
        rest = rest[:m.start()] + rest[m.end():]
        if first < 1 or last <= first:
            raise _err(n, f"fret range '{m.group(0)}' must go low-high, starting at 1 or above")
    for tok in rest.split():
        m = re.fullmatch(r"([1-6]):(\d+(?:,\d+)*)", tok)
        if not m:
            raise _err(n, f"'{tok}' should look like 2:6,8 (string 1-6, 1 = high E, then frets)")
        dots.setdefault(int(m.group(1)), []).extend(int(f) for f in m.group(2).split(","))
    if not dots:
        raise _err(n, "scale has no notes, e.g. 'scale D min pent: 1:5,8 2:6,8'")
    frets = [f for fs in dots.values() for f in fs]
    if first is None:
        first, last = 1, max(12, max(frets))
    elif any(f != 0 and not first <= f <= last for f in frets):
        raise _err(n, f"a note falls outside frets {first}-{last}")
    return ScaleDiagram(name.strip(), dots, first, last)


def _parse_tab(n: int, block: list[str]) -> Tab:
    """`block` is the raw lines after 'tab:' up to the next blank line."""
    if not block:
        raise _err(n, "'tab:' has no tab lines after it")
    lines = [ln.expandtabs().rstrip() for ln in block]
    indent = min(len(ln) - len(ln.lstrip()) for ln in lines)
    lines = [ln[indent:] for ln in lines]
    tab = Tab([])
    for offset, ln in enumerate(lines, 1):
        if _TAB_STRING.match(ln):
            if tab.below:
                raise _err(n + offset, "tab string lines must be together, not split by notes")
            tab.strings.append(ln)
        elif tab.strings:
            tab.below.append(ln)
        else:
            tab.above.append(ln)
    if not tab.strings:
        raise _err(n + 1, "no tab lines found (they look like 'A|--4-4-|')")
    if len({len(s) for s in tab.strings}) > 1 or len({s.index("|") for s in tab.strings}) > 1:
        raise _err(n + 1, "tab lines must all be the same length and start in the same column")
    return tab


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
    line = _GROUP.sub(_join_group, line)
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
        elif _canonical_item(tok) is None:
            raise _err(n, f"'{tok.replace('_', ' ')}' isn't a chord, rest or rhythm (notes and directions go on a line starting with '->')")
        elif ending_just_closed:
            raise _err(n, f"'{tok}' comes right after '}}' in the same bar; put a '|' after the '}}'")
        else:
            chords.append(_canonical_item(tok))
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
    raw_lines = text.splitlines()

    def current() -> Section:
        nonlocal section
        if section is None:
            section = Section("", "")
            chart.sections.append(section)
        return section

    i = 0
    while i < len(raw_lines):
        n, line = i + 1, raw_lines[i].strip()
        i += 1
        if not line:
            continue
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
        m = _STRUM.match(line)
        if m:
            current().strum, current().strum_note = _parse_strum(n, m.group(1))
            continue
        m = _SCALE.match(line)
        if m:
            current().items.append(_parse_scale(n, m.group(1), m.group(2)))
            continue
        if line == "tab:":
            block = []
            while i < len(raw_lines) and raw_lines[i].strip():
                block.append(raw_lines[i])
                i += 1
            current().items.append(_parse_tab(n, block))
            continue
        if section is None:
            m = _HEADER.match(line)
            if m:
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
        line = line.replace("\u2192", "->").replace("\u00d7", "x")
        if line.startswith("->"):
            current().items.append(Roadmap(line[2:].strip()))
            continue
        m = _COUNT_ONLY.match(line)
        if m:
            prev = current().items[-1] if current().items else None
            if not isinstance(prev, BarLine) or not prev.bars[-1].repeat_end:
                raise _err(n, f"'{line}' has no ':||' repeat before it to count")
            prev.bars[-1].repeat_count = int(m.group(1) or m.group(2))
            continue
        bars, repeat_open = _parse_bars(n, line, repeat_open)
        current().items.append(BarLine(bars))
    if not chart.sections:
        raise _err(max(1, len(raw_lines)), "chart has no sections")
    return chart
