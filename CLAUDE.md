# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

User-level ZMK firmware configuration for the MoErgo Go60 wireless split keyboard. The actual ZMK source lives at `moergo-sc/zmk`; this repo only holds a keymap + kconfig + build wrapper and is consumed by that ZMK tree to produce a combined-hands `go60.uf2` firmware image.

## Build

Three equivalent ways to build firmware. All produce `go60.uf2` (combined left+right image).

- **GitHub Actions** (primary workflow): any push triggers `.github/workflows/build.yml`. It checks out `moergo-sc/zmk@main` into `src/` alongside this repo, then runs `nix-build config -o combined`. Artifact `go60.uf2` is attached to the workflow run.
- **Local via Docker**: `./build.sh [branch]` (or `build.bat` on Windows). Builds the `Dockerfile` image, which mirrors `moergo-sc/zmk`, checks out `$BRANCH` (default `main`), and runs the nix build. Output `go60.uf2` is written into the repo root with the host user's UID/GID. The image pre-warms the nix store with `main` plus the three most recent tags, and uses the `moergo-glove80-zmk-dev` cachix cache.
- **Local via nix directly** (requires a sibling checkout of `moergo-sc/zmk` at `../src` or passing `--arg firmware`): `nix-build ./config --arg firmware 'import /path/to/zmk/default.nix {}' -o combined`.

To target a different ZMK branch/tag locally, pass it as the first arg to `build.sh`. In CI the ZMK ref is pinned in the workflow file (`ref: main`).

## Architecture

The build is composed, not self-contained:

- `config/default.nix` is the entry point nix-build consumes. It imports a `firmware` argument (the external ZMK tree's `default.nix`) and calls `firmware.zmk.override` twice — once with `board = "go60_lh"` and once with `go60_rh` — both pointing at the same `go60.keymap` and `go60.conf`. It then calls `firmware.combine_uf2` to produce a single UF2 that flashes both halves.
- `config/go60.keymap` — devicetree (`.keymap`) source defining layers, behaviors (hold-tap, tap-dance, macros), input processors, and key bindings. Layer indices are defined at the top as `LAYER_Base`, `LAYER_Keypad`, `LAYER_SymbolNav`, `LAYER_Magic`, `LAYER_Factory`. Edits here are the usual reason to touch this repo.
- `config/go60.conf` — Kconfig flags passed to the Zephyr build (BLE, RGB, pointing, etc.).
- `config/info.json` — physical layout metadata (row/col/x/y per key, including thumb cluster rotations). Used by layout editors/visualizers, not by the firmware build.

Key names in the keymap follow the `L_CxRy` / `R_CxRy` / `L_Tn` / `R_Tn` scheme visible in `info.json` (Left/Right, Column, Row; thumb keys T1–T3).

## Notes

- A prebuilt `go60.uf2` is committed at the repo root; it is overwritten by local builds. Don't hand-edit it.
- README recommends the MoErgo Go60 Layout Editor webapp for most users; this repo is the lower-level path for users who want to edit devicetree directly or add custom behaviors.
- Upstream references: ZMK docs (`zmk.dev/docs`), MoErgo ZMK fork (`github.com/moergo-sc/zmk`).
