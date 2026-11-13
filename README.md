# chord-chart-pdf

Turns a plain-text chord chart into a clean one-page PDF for students. The text is
transcribed from handwritten charts (paper or GoodNotes) and corrected as needed.

```
pip install reportlab
python -m chordchart examples/actor.chart "Actor - Conan Gray.pdf"
```

See `examples/*.chart` for the format (repeats, endings, `%` bars, rests and rhythm figures,
strumming lines, fermatas, tab, scale necks, chord diagrams with barres). Errors start with
`line N:`. Tests: `pip install pytest pypdf && pytest`.

Design notes and the build plan are in `docs/superpowers/`.
