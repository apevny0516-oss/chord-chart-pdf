# chord-chart-pdf

Turns a plain-text chord chart into a clean one-page PDF for students. The text is
transcribed from handwritten charts (paper or GoodNotes) and corrected as needed.

```
pip install reportlab
python -m chordchart examples/actor.chart "Actor - Conan Gray.pdf"
```

Header lines: title, artist, key, tempo (e.g. `tempo: 94`, shown as "Tempo: 94 bpm"), capo, footer.

See `examples/*.chart` for the format (repeats, endings, `%` bars, rests and rhythm figures,
strumming lines, fermatas, tab, scale necks, chord diagrams with barres). Errors start with
`line N:`. Tests: `pip install pytest pypdf && pytest`.

Design notes and the build plan are in `docs/superpowers/`.

Section boxes are coloured by type so students can find a section by colour: verse yellow,
pre-chorus green, chorus blue, post-chorus teal, bridge purple, solo/interlude orange,
tag pink, intro/outro uncoloured. A section's name wins over its letter (`[B] Chorus` is blue).
