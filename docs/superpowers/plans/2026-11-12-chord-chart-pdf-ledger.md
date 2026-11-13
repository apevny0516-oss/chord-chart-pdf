# SDD ledger — plan: /home/claude/chord-chart-pdf/docs/superpowers/plans/2026-11-12-chord-chart-pdf.md
Setup: Ruling: new repo, work on branch feat/renderer instead of a worktree — repo created for this plan, nothing to isolate from — none.
Pre-flight: T2 consumes Shape/Chart/ChartError from T1 — consistent. T3 consumes shapes_for/draw_diagram from T2 — consistent. T4 consumes parse/render — consistent.
Task 1: Ruling: plan says fingers are [-1-4] but the spec sample uses 'x2--34' — fingers accept x too (spec wins) — none; a stray x in fingers is ignored when drawing.
Task 1: complete (commits 9b3a94d..ec30238, tests: python -m pytest tests/test_parser.py -q → 12 passed in 0.02s)
Task 2: Ruling: added chordchart/text.py (font registration, sharp/flat typography) not in the plan's file list — both diagrams and renderer need it — none.
Task 2: complete (commits ec30238..d0e510a, tests: python -m pytest tests/test_diagrams.py tests/test_parser.py -q → 17 passed in 0.09s)
Task 3: Ruling: chord diagrams sit right-aligned in the header band (own row only when they'd take over half the width), not a row under the header — saves ~75pt so one-page charts stay one page — purely visual; Andrew sees it in the sample.
Task 3: Ruling: row height is 34pt fixed + 12pt spacing that shrinks (down to 20%) so a chart that nearly fits one page does, instead of the plan's flat 46pt — students want one page — tight spacing on dense charts.
Task 3: complete (commits d0e510a..fcf4a08, tests: python -m pytest -q → 22 passed in 0.21s)
Task 4: complete (commits fcf4a08..ae17998, tests: python -m pytest -q → 23 passed in 0.38s)
Final review: fresh reviewer (opus) — 0 Critical, 6 Important, 7 Minor.
Final: fixed crowded bars overlapping barlines — test_crowded_rows_fit_at_readable_size RED→GREEN, suite 63/63
Final: fixed long roadmap running off page — test_long_roadmap_wraps RED→GREEN, suite 63/63
Final: fixed non-chord text drawn as chords — test_non_chord_text_is_an_error RED→GREEN, suite 63/63
Final: fixed ending dropped after '}' / empty ending — test_bad_ending_is_an_error RED→GREEN, suite 63/63
Final: fixed title/artist colliding with capo/diagrams — test_long_title_moves_diagrams_out_of_header RED→GREEN, suite 63/63
Final: fixed repeat-count spellings becoming a bar — test_repeat_count_spellings RED→GREEN, suite 63/63
Final: Ruling: two diagrams with the same name (two G/B voicings) are drawn as-is — the spec sample asks for it — students can't tell which voicing is which without a note.
Final: Ruling: diagram frets are one character, so shapes at fret 10+ can't be written — format limit, errors rather than drops — high-position shapes need a format change later.
Final: Ruling: header keys are case-sensitive and must precede sections — strict but loud — a typo costs one error message.
Final: Ruling: a roadmap word equal to a section label is drawn as that label's box — plan defines it — "play A softly" boxes the A.
Final: Ruling: 5–6 bar rows use narrower bars that don't align with 4-bar rows — plan specifies it — slightly uneven look.
Final: minor (deferred): '||:' never closed is accepted silently
Final: minor (deferred): unknown-diagram-chord error has no line number
Final: minor (deferred): CLI shows a traceback for a missing file, unwritable output, or non-UTF-8/BOM input
Final: minor (deferred): an empty section's header can end a page
Final: minor (deferred): spacing gets very cramped at the minimum scale; a 0.4 floor would look better
Final: minor (deferred): 'capo: 0' prints "Capo 0"
Final: minor (deferred): DejaVu font path is Linux-only; elsewhere sharps/flats fall back to # and b
