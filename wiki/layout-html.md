# HTML Layout Viewer

`wiki/layout.html` — a single self-contained HTML page showing every human-facing layer
with a tab/arrow switcher. An alternative to the SVG popup viewer
([layer-popup](layer-popup.md)) that handles multi-line legends and CSS styling.

## Generate

```bash
make layout-html     # regenerates wiki/layout.html (runs ./draw.sh first if needed)
# or directly:
python3 tools/gen-layout-html.py
```

Open it with any browser: `open wiki/layout.html`.

## Sources

| Input | Used for |
|-------|----------|
| `keymap-drawer/keymap.yaml` | Layer key bindings + combos (produced by `./draw.sh` / `make draw`) |
| `config/info.json` | Physical key positions, including thumb-cluster rotation |

The script (`tools/gen-layout-html.py`) maps each layer's 60-element key array onto the 60
physical positions from `info.json` (position index `i` ↔ `layout[i]`), so it always
matches the real geometry.

## Which layers are shown

Nine human-facing layers, in this order: **1 HRM_macOS, 2 Typing, 3 Autoshift, 4 Cursor,
5 Keypad, 6 Symbol, 7 Mouse, 8 Magic, 9 fn**. The `EXCLUDE` set in `gen-layout-html.py`
drops the per-finger HRM implementation layers, the Mouse speed variants
(Slow/Fast/Warp), and Gaming. Edit that set to change the selection.

## Controls & legend

| | |
|--|--|
| `Tab` | Cycle how many layers show at once: **1 → 2 → 4** (sliding window) |
| `←` `→` | Move the window by one layer |
| Number keys `1`–`9` / bottom list | Jump straight to that layer |
| Blue key | Layer switch (tap or hold) |
| Amber sub-label | Hold = modifier |
| Pink key | Held key that activates the current layer |
| `▽` faint key | Transparent (falls through to base) |
| Top-right number | Physical position index (0–59) |

The numbered list at the bottom mirrors the SVG popup's nav: each layer's number is its
`1`–`9` keyboard shortcut.

## Modifier glyphs

Modifier and nav-key labels are rendered as macOS glyphs (no custom font needed — these are
standard Unicode that the system font renders): `⌘` Cmd, `⌥` Opt, `⇧` Shift, `⌃` Ctrl,
`⇥` Tab, `↩` Enter, `⌫` Bksp, `⌦` Del, `⎋` Esc, `␣` Space, `⇪` Caps, `← → ↑ ↓`. Home-row-mod
holds (which arrive as `behavior_name MOD`) collapse to just the modifier glyph. The mapping
lives in `MOD_SYMBOLS` / `KEY_SYMBOLS` / `symbolize()` in `gen-layout-html.py`.

## Keeping it fresh

After editing `config/go60.keymap`, run `make draw && make layout-html` to regenerate both
the SVGs and this HTML page.
