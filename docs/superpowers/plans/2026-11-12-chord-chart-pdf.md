# Chord Chart PDF Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a plain-text chord chart into a clean letter-size PDF for students.

**Architecture:** A parser turns the text format into a small dataclass model; a ReportLab renderer draws that model directly on a canvas (bars, repeat signs, ending brackets, section boxes, chord diagrams). A CLI wires them together.

**Tech Stack:** Python 3, ReportLab (drawing), pytest + pypdf (tests), pdftoppm (visual check).

**Spec:** `docs/superpowers/specs/2026-11-12-chord-chart-pdf-design.md`

## Global Constraints

- Page: US Letter portrait, 0.6 in margins.
- Default 4 bars per row; header key `bars_per_line` overrides.
- A source line of up to `bars_per_line + 2` bars stays on one row (narrower bars); longer lines wrap in rows of `bars_per_line`.
- Section box colors by first letter of label: A `#FFF27A`, B `#7DF3FF`, C `#FF8AF3`, D `#A8F08A`, other `#DDDDDD`; black 1.5 pt border.
- Every parse error raises `ChartError` whose message starts with `line N:`.
- Nothing in the source is silently dropped: unknown header keys and unparseable lines are errors.
- No branding; `footer:` header renders one centered footer line if present.
- Package name `chordchart`; project root `/home/claude/chord-chart-pdf`; `git init` in Task 1.

## Review Focus

1. Malformed line (unclosed `{`, `:||` without `||:`) → `ChartError` with line number, not a traceback or a blank bar. (Task 1)
2. `diagrams:` names a chord not in the library and without a `diagram` line → `ChartError` naming the chord. (Task 2)
3. Bar with 3–4 chords or a long name (`F#m7b5`) → text shrinks to fit inside its bar, never overlaps a barline. (Task 3)
4. Chart longer than one page → continues on page 2; a section header is never the last thing on a page. (Task 3)
5. Missing `title`/`artist`/`capo` → renders without that header part; no "None" text. (Task 3)

---

## File Structure

- `chordchart/model.py` — dataclasses only.
- `chordchart/parser.py` — `parse(text) -> Chart`, `ChartError`.
- `chordchart/diagrams.py` — chord shape library, shape resolution, diagram drawing.
- `chordchart/render.py` — `render(chart, out_path)`.
- `chordchart/__main__.py` — CLI.
- `examples/actor.chart` — the spec's sample, verbatim.
- `tests/test_parser.py`, `tests/test_diagrams.py`, `tests/test_render.py`.

### Task 1: Model and parser

**Files:** Create `chordchart/__init__.py`, `chordchart/model.py`, `chordchart/parser.py`, `examples/actor.chart`, `tests/test_parser.py`

**Interfaces — Produces:**

```python
@dataclass
class Bar:
    chords: list[str]            # ["Am", "G"]; ["%"] for a simile bar
    repeat_start: bool = False   # ||: before this bar
    repeat_end: bool = False     # :|| after this bar
    repeat_count: int | None = None  # the N of "xN" after :||
    ending: tuple[int, ...] | None = None  # (1,2,3) from {1,2,3: G}
    final: bool = False          # || after this bar

@dataclass
class BarLine:  bars: list[Bar]
@dataclass
class Roadmap:  text: str        # text after "->", e.g. "A1 -> B"
@dataclass
class Section:
    label: str                   # "A1"
    name: str                    # "Verse 2" or ""
    items: list[BarLine | Roadmap]
@dataclass
class Shape:
    name: str; frets: str        # 6 chars of x/0-9, low E first
    fingers: str | None = None   # 6 chars of -/1-4
@dataclass
class Chart:
    title: str | None; artist: str | None; capo: int | None
    footer: str | None; bars_per_line: int   # default 4
    sections: list[Section]
    custom_shapes: list[Shape]   # from "diagram NAME: FRETS [FINGERS]", in order
    diagram_names: list[str]     # from "diagrams: A, B"

class ChartError(ValueError): ...
def parse(text: str) -> Chart
```

Grammar: header `key: value` lines (keys `title`, `artist`, `capo`, `footer`, `bars_per_line`) before the first section; `[LABEL] name` starts a section; `-> text` is a Roadmap; `diagram`/`diagrams` lines may appear anywhere; any other non-blank line is a bar line. Bar tokens split on `|`; `{n,n: bars}` may wrap one or more `|`-separated bars and marks each with `ending`.

- [ ] **Step 1: Write failing tests** in `tests/test_parser.py`:

```python
ACTOR = open("examples/actor.chart").read()

def test_header():
    c = parse(ACTOR)
    assert (c.title, c.artist, c.capo, c.bars_per_line) == ("Actor", "Conan Gray", 4, 4)

def test_sections():
    c = parse(ACTOR)
    assert [(s.label, s.name) for s in c.sections] == [
        ("A", ""), ("A", "Verse"), ("A1", "Verse 2"), ("B", "Chorus"), ("C", "Bridge")]

def test_repeat_with_count():
    bars = parse(ACTOR).sections[1].items[0].bars
    assert [b.chords for b in bars] == [["C"], ["Am"], ["Em"], ["G"]]
    assert bars[0].repeat_start and bars[3].repeat_end and bars[3].repeat_count == 4

def test_endings():
    bars = parse(ACTOR).sections[2].items[0].bars
    assert len(bars) == 5
    assert bars[3].ending == (1, 2, 3) and bars[3].repeat_end
    assert bars[4].ending == (4,) and bars[4].chords == ["E7"] and bars[4].final

def test_two_chord_bar_simile_and_roadmap():
    ch = parse(ACTOR).sections[3]
    assert ch.items[0].bars[3].chords == ["Am", "G"]
    assert ch.items[1].bars[2].chords == ["%"]
    assert len(ch.items[2].bars) == 8 and ch.items[2].bars[7].final
    assert ch.items[3] == Roadmap("A1 -> B")

def test_diagram_lines():
    c = parse(ACTOR)
    assert c.custom_shapes == [Shape("G/B", "x20033", "x2--34"), Shape("G/B", "x2000x", None)]
    assert c.diagram_names == ["Dm"]

@pytest.mark.parametrize("bad", [
    "[A]\n||: C | {1,2: G :||",        # unclosed brace
    "[A]\nC | G :||",                  # repeat end without start
    "tempo: 120\n[A]\nC |",            # unknown header key
    "C | G |",                         # bars before any section
    "[A]\ndiagram G: x2003",           # frets not 6 chars
    "",                                # empty
])
def test_errors_have_line_numbers(bad):
    with pytest.raises(ChartError, match=r"^line \d+:"):
        parse(bad)
```

- [ ] **Step 2:** Run `pytest tests/test_parser.py -v` → FAIL (import error).
- [ ] **Step 3:** Implement `model.py` and `parser.py` to the interfaces above; write `examples/actor.chart` from the spec verbatim. A `:||` whose matching `||:` is on an earlier line of the same section is allowed.
- [ ] **Step 4:** Run `pytest tests/test_parser.py -v` → PASS.
- [ ] **Step 5:** `git init && git add -A && git commit -m "feat: chart text parser"`

### Task 2: Chord shapes and diagram drawing

**Files:** Create `chordchart/diagrams.py`, `tests/test_diagrams.py`

**Interfaces:**
- Consumes: `Shape`, `Chart`, `ChartError`.
- Produces:

```python
LIBRARY: dict[str, Shape]   # C A Am G E Em D Dm F E7 A7 D7 G7 B7 C7 Am7 Em7 Dm7 Cmaj7 Fmaj7 Bm G/B D/F#
def shapes_for(chart: Chart) -> list[Shape]
    # custom_shapes in order, then each diagram_names entry not already
    # covered by a custom shape, from LIBRARY. Unknown name -> ChartError.
def draw_diagram(canvas, shape: Shape, x: float, y: float, width: float) -> float
    # draws name, nut/fret grid (4 frets; base-fret label if lowest fretted > 4),
    # x/o markers, dots with finger numbers inside; returns height used.
```

- [ ] **Step 1: Failing tests:**

```python
def test_library_shapes_valid():
    for s in LIBRARY.values():
        assert re.fullmatch(r"[x0-9]{6}", s.frets)
        assert s.fingers is None or re.fullmatch(r"[-1-4]{6}", s.fingers)
    assert LIBRARY["Dm"].frets == "xx0231" and LIBRARY["C"].frets == "x32010"

def test_custom_wins_and_library_fills():
    names = [(s.name, s.frets) for s in shapes_for(parse(ACTOR))]
    assert names == [("G/B", "x20033"), ("G/B", "x2000x"), ("Dm", "xx0231")]

def test_unknown_chord_named_in_error():
    with pytest.raises(ChartError, match="Zm9"):
        shapes_for(parse("[A]\nC |\ndiagrams: Zm9"))

def test_draw_returns_height(tmp_path):
    c = Canvas(str(tmp_path / "d.pdf"))
    assert draw_diagram(c, LIBRARY["Dm"], 72, 600, 60) > 0
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** `git commit -am "feat: chord shape library and diagrams"` (after `git add`).

### Task 3: PDF renderer

**Files:** Create `chordchart/render.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: `Chart` model, `shapes_for`, `draw_diagram`.
- Produces: `def render(chart: Chart, out_path: str) -> None`

Layout decisions: header = title bold 24 pt left, artist 13 pt beneath, `Capo N` right-aligned in green `#5BB12F` (omit any missing part). Diagram row under the header, 62 pt wide each, only if `shapes_for` is non-empty. Each section: colored label box + name in small caps-style uppercase 11 pt, then its rows. Row height 46 pt; chords Helvetica-Bold 20 pt, left-aligned at bar start + 8 pt; multiple chords spaced evenly across the bar; font shrinks until text fits its slot. `%` drawn as a slash with two dots, centered. Repeat signs = thick+thin lines with two dots; `xN` above the end repeat; ending bracket = line above the bar(s) with a down-tick at left and the numbers `1, 2, 3.`; consecutive bars with the same ending share one bracket. Roadmap rows: `→` arrows, and any token equal to a section label is drawn as that label's colored box. `#`/`b` after a note letter render as ♯/♭ when DejaVu Sans is installed, ASCII otherwise. Keep a section header with its first row; start a new page when the next block doesn't fit.

- [ ] **Step 1: Failing tests** (text via `pypdf.PdfReader(path).pages[i].extract_text()`):

```python
def test_actor_renders_one_page(tmp_path):
    out = tmp_path / "actor.pdf"; render(parse(ACTOR), str(out))
    r = PdfReader(out); text = r.pages[0].extract_text()
    assert len(r.pages) == 1
    for s in ["Actor", "Conan Gray", "Capo 4", "VERSE 2", "CHORUS", "BRIDGE",
              "E7", "G/B", "Dm", "x4", "doesn't resolve to C"]:
        assert s in text

def test_missing_header_parts(tmp_path):
    out = tmp_path / "x.pdf"; render(parse("[A]\nC | G |"), str(out))
    assert "None" not in PdfReader(out).pages[0].extract_text()

def test_long_chart_paginates(tmp_path):
    src = "title: Long\n" + "\n".join(f"[A] Part {i}\nC | G | Am | F |" for i in range(40))
    out = tmp_path / "l.pdf"; render(parse(src), str(out))
    r = PdfReader(out); assert len(r.pages) >= 2
    all_text = "".join(p.extract_text() for p in r.pages)
    assert all(f"PART {i}" in all_text for i in range(40))

def test_crowded_bar_fits(tmp_path):
    # fitted_font_size(chords, slot_width, base=20) is the helper under test
    from chordchart.render import fitted_font_size
    assert fitted_font_size(["F#m7b5"], 40) < 20
    assert fitted_font_size(["C"], 120) == 20

def test_footer(tmp_path):
    out = tmp_path / "f.pdf"; render(parse("footer: AGP Music\n[A]\nC |"), str(out))
    assert "AGP Music" in PdfReader(out).pages[0].extract_text()
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement `render` and `fitted_font_size(chords: list[str], slot_width: float, base: float = 20) -> float`. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: PDF renderer`.

### Task 4: CLI and visual check

**Files:** Create `chordchart/__main__.py`; add one test to `tests/test_render.py`

**Interfaces — Produces:** `python -m chordchart IN.chart OUT.pdf`; exit 0 on success; on `ChartError` print the message to stderr and exit 1.

- [ ] **Step 1: Failing test:**

```python
def test_cli(tmp_path):
    out = tmp_path / "a.pdf"
    assert subprocess.run([sys.executable, "-m", "chordchart", "examples/actor.chart", str(out)]).returncode == 0
    assert out.exists()
    bad = tmp_path / "bad.chart"; bad.write_text("[A]\nC | G :||")
    p = subprocess.run([sys.executable, "-m", "chordchart", str(bad), str(out)], capture_output=True, text=True)
    assert p.returncode == 1 and p.stderr.startswith("line 2:")
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** `pytest -v` → all PASS.
- [ ] **Step 5:** Visual check: `pdftoppm -png -r 80 actor.pdf actor` and look at the image; fix any overlap, clipped bracket, or misaligned repeat sign, compare against the handwritten original for anything dropped.
- [ ] **Step 6:** Commit `feat: CLI`; send `actor.pdf` to Andrew.

## Follow-up (not in this plan)
Package as a skill once Andrew approves the look.
