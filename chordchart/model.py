"""Data model for a chord chart."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Bar:
    chords: list[str]
    repeat_start: bool = False
    repeat_end: bool = False
    repeat_count: int | None = None
    ending: tuple[int, ...] | None = None
    final: bool = False


@dataclass
class BarLine:
    bars: list[Bar]


@dataclass
class Roadmap:
    text: str


@dataclass
class Section:
    label: str
    name: str
    items: list = field(default_factory=list)   # BarLine | Roadmap | ScaleDiagram | Tab
    strum: list[str] | None = None              # rhythm tokens, e.g. ["8>", "8"]
    strum_note: str | None = None


@dataclass
class Shape:
    name: str
    frets: str
    fingers: str | None = None


@dataclass
class Chart:
    title: str | None = None
    artist: str | None = None
    capo: int | None = None
    key: str | None = None
    tempo: str | None = None     # digits, e.g. "94"
    footer: str | None = None
    bars_per_line: int = 4
    sections: list[Section] = field(default_factory=list)
    custom_shapes: list[Shape] = field(default_factory=list)
    diagram_names: list[str] = field(default_factory=list)


@dataclass
class ScaleDiagram:
    name: str
    dots: dict[int, list[int]]    # string number (1 = high E) -> frets
    first_fret: int = 1
    last_fret: int = 12


@dataclass
class Tab:
    strings: list[str]            # ASCII tab lines, equal length, label before the first '|'
    above: list[str] = field(default_factory=list)   # annotation lines, column-aligned
    below: list[str] = field(default_factory=list)
