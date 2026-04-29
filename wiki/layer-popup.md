# Layer Popup Viewer

A native macOS window that displays Go60 keyboard layer SVGs for quick reference. Invoke it with a hotkey app; it cold-starts in under a second.

## Files

| Path | Purpose |
|------|---------|
| `tools/layer-popup.swift` | Source — NSWindow + WKWebView, reads SVGs, serves HTML |
| `tools/layer-popup` | Compiled binary (gitignored, built by `make layers`) |

## Build

```bash
make layers          # compiles if needed, then launches
# or compile only:
swiftc tools/layer-popup.swift -o tools/layer-popup
```

The Makefile rule is a proper dependency target — it only recompiles when `layer-popup.swift` is newer than the binary.

## Running

```bash
# explicit layers directory
U_KBD_KEYMAP=/path/to/keymap-drawer/layers ./tools/layer-popup

# from repo root (fallback path resolves automatically)
./tools/layer-popup
```

Point your hotkey app (Raycast, Alfred, skhd, etc.) at the compiled binary. No arguments needed if run from the repo root.

### `U_KBD_KEYMAP`

The env var must point to a **directory** containing `.svg` files. If unset, the binary falls back to `../keymap-drawer/layers/` relative to itself — which works when the binary lives at `tools/layer-popup` inside the repo.

To regenerate the SVGs from the keymap source:

```bash
make draw
```

## Controls

| Key | Action |
|-----|--------|
| `←` / `→` | Navigate layers |
| `Tab` | Cycle layout mode |
| `Esc` | Close |

## Layout modes

Cycle through three views with Tab:

| Mode | Display |
|------|---------|
| **2×2** (default) | 2 columns × 2 rows — 4 layers at a time |
| **1×2** | 1 row × 2 columns — 2 layers side-by-side |
| **1×1** | Single layer, scaled to fill window height, centered |

Arrow navigation moves one layer at a time (sliding window) in all modes.

## How it works

1. At launch, Swift reads every `.svg` file from the layers directory and embeds them as JS data (backtick-escaped template literals) in a self-contained HTML string.
2. An `NSWindow` with a `WKWebView` loads that HTML string directly — no HTTP server, no temp files.
3. All key handling (arrows, Tab) is done via a JS `keydown` listener inside the page; Escape is caught by the `NSWindow` subclass before WKWebView sees it.
4. Layout switching and navigation update the DOM in-place — no page reloads.

The binary is ~100 KB and starts in roughly 0.4 s of CPU time on Apple Silicon.
