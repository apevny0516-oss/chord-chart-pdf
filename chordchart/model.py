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
    items: list[BarLine | Roadmap] = field(default_factory=list)


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
    footer: str | None = None
    bars_per_line: int = 4
    sections: list[Section] = field(default_factory=list)
    custom_shapes: list[Shape] = field(default_factory=list)
    diagram_names: list[str] = field(default_factory=list)
