---
description: Render the Go60 physical key layout with POS_* names and position indices.
---

Render an ASCII diagram of the Go60 physical key layout. Each cell shows its `POS_*` name on one line and the integer position index on the next.

## Source of truth

- `config/go60.keymap` — the `#define POS_*` block (around lines 60–129) maps every position name to its integer index.
- `tools/key-id.py` — the `ROWS` list (lines ~170–183) defines the physical grid order, and `THUMBS` (lines ~185–188) defines the thumb display order.

Always re-read these before drawing, in case they change.

## Layout shape

- **4 main rows × 12 cells**: 6 left-hand columns (`C6 → C1`), a gap, then 6 right-hand columns (`C1 → C6`). So column 6 is the outer/pinky side and column 1 is the inner/index side.
- **Row 5** (small bottom strip): 3 left keys (`LH_C4R5 LH_C3R5 LH_C2R5`), gap, 3 right keys (`RH_C2R5 RH_C3R5 RH_C4R5`).
- **Thumb cluster** (6 keys total): physical left-to-right order, taken straight from `THUMBS`:
  `LH_T3  LH_T2  LH_T1  │  RH_T1  RH_T2  RH_T3`
  (outer→inner on the left, inner→outer on the right — `T1` is the innermost thumb on each side, `T3` is the outermost.)

## Output format

- One ASCII grid using box-drawing characters (`┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ─ │`).
- Two-line cells: position name on top, `(index)` on bottom.
- Render the two halves side-by-side with a clear gap between them.
- After the diagram, add a short reading guide explaining `Cn` (column, 1=index, 6=pinky/outer), `Rn` (row, 1=number row, 4=bottom main row, 5=small bottom strip), and the thumb numbering convention.

Do not show key bindings or layer functions — this command is purely about physical positions.
