# Notation additions (approved 2026-11-12, "go ahead with all")

Source: five more handwritten charts (Castle in Hollywood, Jigsaw, iloveitiloveitiloveit,
Layla, Cigarette Smoke). Three use notation v1 can't draw. Approach unchanged
(handwriting -> text -> PDF); this adds text syntax + drawing for six things.

1. Strumming line, per section: `strum: 8> 8 8 8> 8 8 8> 8 "w/ palm muting"`.
   Drawn beside the section name as rhythm slashes with beams, accents, and the note.
2. Rhythm inside a bar: rests (`r4`, `r2`, ...) and rhythm figures `(8> 8 8> 8)` are
   bar items alongside chords: `Am r4 r2`, `E | (8> 8 8> 8) r2 ||`.
   Rhythm tokens: 1 2 4 8 16, optional `.` dotted, `>` accent, `r` prefix for rests.
3. Fermata: `C(fermata)`.
4. Scale diagram: `scale D min pent: 1:5,8 2:6,8 3:5,7` (string:frets, string 1 = high E),
   optional `frets 3-9`; default neck is frets 1-12. Horizontal neck, drawn where written.
5. Tab riff: a `tab:` line followed by ASCII tab lines (and optional annotation lines
   above/below, column-aligned) up to the next blank line. Drawn as a real tab staff.
6. Barre lines in chord diagrams, detected when one finger number covers 2+ strings at one fret.

Also: charts may have bars with no section header (Layla); `[CHORUS 1]`-style word labels
are grey boxes and are recognised in roadmap lines.

Approved readings: Castle strumming accents on eighths 1, 4, 7; Castle "Am" bars are one
hit then rests.

Tasks: (1) parser+model, (2) rhythm/rest/fermata drawing in bars and strum line,
(3) scale neck, (4) tab staff, (5) barre lines, (6) render the three held-back charts.
