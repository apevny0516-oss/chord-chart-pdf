# Handwritten Chord Chart → Clean PDF: Design

## Intent
Andrew writes chord charts by hand (paper or GoodNotes). He wants clean PDF
charts to hand to students without changing how he writes.

## Goals
- Input: photo/export of natural handwriting. No template.
- Claude transcribes to a short plain-text chart, flags guesses; Andrew corrects text.
- A renderer turns the text into a letter-size PDF.

## Non-goals (v1)
- Band Teacher Assistant integration or audio sync.
- Branding (only an optional footer line).
- Rhythm slashes/notation, lyrics, transposition.
- Packaging as a skill (follow-up once the look is approved).

## Anti-goals
- Anything that slows down the handwriting step.
- Output that silently drops something he wrote (roadmap notes, endings).

## Approaches
1. **Natural handwriting → text → rendered PDF (picked).** No writing friction;
   text step makes corrections one-line edits.
2. GoodNotes template with fixed bar boxes: solves a reading problem that
   doesn't exist; adds friction.
3. Typing shorthand directly: fastest, but gives up handwriting.

## Output look (approved)
- Header: title, artist, capo.
- Four bars per line.
- Section label boxes colored by letter: A yellow, B cyan, C magenta.
- Proper repeat signs, `xN` counts, numbered ending brackets, `%` simile bars.
- Roadmap notes kept as written (`-> A1 -> B`, free text).
- Chord diagrams: standard library by default; his sketched voicing wins.
- Optional footer line; none by default.

## Text format (approved sample)
```
title: Actor
artist: Conan Gray
capo: 4

[A]
||: C | Am | Em | G :||

[A] Verse
||: C | Am | Em | G :|| x4

[A1] Verse 2
||: C | Am | Em | {1,2,3: G} :|| {4: E7} ||

[B] Chorus
||: F | G | E7 | Am G :||
C G/B | Am | % |
F | G | Am | % | F | G | C | % ||
-> A1 -> B

[C] Bridge
||: Am | Em | F | G :|| x2
Dm | % | G | % |
-> B (doesn't resolve to C)

diagram G/B: x20033 x2--34
diagram G/B: x2000x
diagrams: Dm
```
Approved readings: chorus first line is a plain repeat (played twice);
Verse 2's fourth pass replaces the G bar with E7.

## Left to the builder
Fonts, exact spacing, diagram placement (Claude's call: a row under the header).
