# Go60 ZMK Config — Project Documentation

In-depth reference for working on this repository. For end-user instructions (template, GitHub Actions artifact, flashing) see `README.md`.

## Repository purpose

User-level ZMK firmware configuration for the **MoErgo Go60** wireless split keyboard. The actual ZMK source lives at [`moergo-sc/zmk`](https://github.com/moergo-sc/zmk); this repo only holds:

- a keymap (`config/go60.keymap`)
- a Kconfig file (`config/go60.conf`)
- a physical layout description (`config/info.json`)
- a small Nix entrypoint (`config/default.nix`)
- build wrappers and CI

These files are consumed by the upstream ZMK tree to produce a single combined-hands `go60.uf2` firmware image.

## Repository layout

```
.
├── config/
│   ├── default.nix       # Nix entrypoint; glues this config to upstream ZMK
│   ├── go60.keymap       # Devicetree keymap (the file you edit most)
│   ├── go60.conf         # Kconfig flags for the Zephyr build
│   └── info.json         # Physical layout (for visualizers, not the build)
├── .github/workflows/
│   ├── build.yml         # Builds firmware on every push, attaches go60.uf2
│   └── draw.yml          # Renders keymap.svg on keymap changes
├── keymap-drawer/        # Generated visualization (yaml + svg)
├── Dockerfile            # Local build environment
├── build.sh / build.bat  # Run a local Docker build
├── flash.sh              # Build, then copy go60.uf2 to mounted bootloader drive
├── draw.sh               # Render keymap.svg locally via keymap-drawer
├── go60.uf2              # Last-built firmware (committed, overwritten on rebuild)
└── README.md
```

## How the build is composed

The build is **layered**, not self-contained:

1. **Upstream ZMK** (`moergo-sc/zmk`) provides the Zephyr build, board definitions for `go60_lh` / `go60_rh`, and the `firmware` Nix expression.
2. **`config/default.nix`** receives that `firmware` argument and calls `firmware.zmk.override` twice — once per hand — feeding both the same `go60.keymap` and `go60.conf`. It then calls `firmware.combine_uf2` to glue both halves into a single UF2 the bootloader can split apart at flash time.
3. **`go60.keymap` + `go60.conf`** are the only inputs that change in normal use.

This separation is why building locally requires either Docker (which clones ZMK inside) or a sibling checkout of `moergo-sc/zmk`.

## Build paths

All three paths produce the same `go60.uf2` (combined left + right image).

### A. GitHub Actions (default)

Pushing any commit triggers `.github/workflows/build.yml`, which:

1. Checks out this repo and `moergo-sc/zmk@main` into `src/`.
2. Installs Nix and wires up the `moergo-glove80-zmk-dev` Cachix cache (so prebuilt Zephyr artifacts download instead of compile).
3. Runs `nix-build config -o combined`.
4. Uploads `go60.uf2` as a workflow artifact.

To consume: open the run, scroll to **Artifacts**, download `go60.uf2`.

### B. Local Docker (`./build.sh`)

```bash
./build.sh                # build against ZMK main
./build.sh <ref>          # build against a specific ZMK branch / tag / SHA
REBUILD=1 ./build.sh      # force a fresh `docker build`
SKIP_FETCH=1 ./build.sh   # skip `git fetch origin` inside the container
```

How it works:

- The Docker image (`Dockerfile`) bootstraps a Nix environment, mirrors `moergo-sc/zmk` into `/zmk`, and worktrees it at `/src`.
- `build.sh` reuses the image if it exists; pass `REBUILD=1` to rebuild.
- A named Docker volume (`go60-zmk-nix-store`) is mounted at `/nix` so the Nix store **persists across runs**. First run populates it from Cachix; later runs are dramatically faster.
- The entrypoint checks out the requested ZMK ref, runs `nix-build` with `-j$(nproc) --cores 8`, and copies `go60.uf2` back to the host with the host's UID/GID.

### C. Native Nix (fastest iteration)

Requires Nix on the host plus a sibling checkout of `moergo-sc/zmk`:

```bash
git clone https://github.com/moergo-sc/zmk ../zmk
nix-env -iA cachix -f https://cachix.org/api/v1/install
cachix use moergo-glove80-zmk-dev

nix-build ./config --arg firmware 'import ../zmk/default.nix {}' -o combined
cp combined/go60.uf2 .
```

Compared to Docker: no container overhead, native arch (faster on Apple Silicon), Nix store lives in `/nix/store` host-wide and is shared across projects.

## Flashing

```bash
./flash.sh                # build + flash
SKIP_FETCH=1 ./flash.sh   # skip the git fetch
./flash.sh <ref>          # build against a specific ZMK ref, then flash
```

`flash.sh` runs `./build.sh "$@"`, then looks for `/Volumes/GLV80LHBOOT` or `/Volumes/GLV80RHBOOT` and copies `go60.uf2` onto whichever is mounted. The combined UF2 contains both halves; the bootloader on each side picks out its own.

To put the keyboard into bootloader mode: hold the `magic` key and tap the `&bootloader` key on the Magic layer (`config/go60.keymap`, left half, row 2).

## The keymap

`config/go60.keymap` is a Devicetree (`.keymap`) source with a C preprocessor pass on top. Top-level structure:

- **Layer indices** (`#define LAYER_Base 0`, …) — symbolic names referenced by bindings.
- **`input_processors`** — pointer-device transforms, e.g. `zip_click_to_right_click_mapper`.
- **`behaviors`** — custom hold-taps, tap-dances, mod-morphs. Examples in this repo:
  - `magic` — hold = momentary layer, tap = RGB status macro.
  - `keypad_td`, `symbol_nav_td` — single-tap = momentary, double-tap = toggle.
  - `bt_0`–`bt_3` — single-tap = select BLE profile, double-tap = disconnect it.
  - `quote_flip` — mod-morph: tap = `"`, Shift+tap = `'`.
- **`macros`** — composed sequences (`rgb_ug_status_macro`, `bt_select_*`).
- **`keymap`** — the actual layer grids of bindings.
- **`&cirque_*_listener` overrides** — per-layer pointing-device tweaks (scaling, scroll mapping).

Layer roster:

| Index | Name        | Purpose                                                  |
| ----- | ----------- | -------------------------------------------------------- |
| 0     | `Base`      | Standard typing layer.                                   |
| 1     | `Keypad`    | F-keys, arrows, numpad, common Ctrl-shortcuts.           |
| 2     | `SymbolNav` | Symbols (paren/brace/bracket/etc.) and navigation.       |
| 3     | `Magic`     | RGB, Bluetooth profile management, bootloader, sys-reset.|
| 4     | `Factory`   | Factory test pattern (rarely touched).                   |

### Key naming convention

Keys in `info.json` and key positions are named `<L|R>_C<n>R<n>` (Left/Right hand, Column, Row) for the main grid, and `<L|R>_T<n>` for thumb keys. So `R_C5R3` is the right-hand pinky home-row, and `L_T1` is the left-hand inner thumb.

### Adding a behavior

Pattern: define the behavior inside the existing `behaviors { }` block, then reference it from a layer binding. Example (already in the keymap):

```dts
quote_flip: quote_flip {
    compatible = "zmk,behavior-mod-morph";
    #binding-cells = <0>;
    bindings = <&kp DQT>, <&kp SQT>;
    mods = <(MOD_LSFT|MOD_RSFT)>;
};
```

Then in a layer: `&quote_flip` instead of `&kp SQT`.

For unfamiliar behaviors (hold-tap flavors, sticky keys, combos, capsword, etc.) consult the [ZMK behaviors docs](https://zmk.dev/docs/keymaps/behaviors).

## Keymap visualization

`./draw.sh` regenerates `keymap-drawer/keymap.svg` from the current keymap. Pipeline:

1. `keymap parse -z config/go60.keymap` parses the Devicetree into intermediate YAML.
2. The script prepends `layout: {qmk_info_json: config/info.json}` so [keymap-drawer](https://github.com/caksoylar/keymap-drawer) uses the real Go60 geometry (thumb-cluster rotations etc.) instead of guessing.
3. `keymap draw` renders the YAML to SVG.

The same pipeline runs in CI via `.github/workflows/draw.yml` on every push that touches the keymap or `info.json`. The bot pushes a follow-up `[Draw] update keymap rendering` commit with the regenerated files.

To install locally: `pipx install keymap-drawer`.

## CI workflows

| Workflow             | Trigger                               | Output                                     |
| -------------------- | ------------------------------------- | ------------------------------------------ |
| `build.yml`          | Any push, PR, or manual dispatch.     | `go60.uf2` as a run artifact.              |
| `draw.yml`           | Push touching keymap/info.json/itself | Commits regenerated `keymap-drawer/*`.     |

`draw.yml` requires the repo's Actions workflow permissions to be set to **Read and write** (Settings → Actions → General).

## Configuration files reference

### `config/go60.conf`

Kconfig switches passed to the Zephyr build. One `CONFIG_FOO=y` per line. Useful flags:

- `CONFIG_BT_*` — Bluetooth radio behavior.
- `CONFIG_ZMK_RGB_*` — RGB underglow.
- `CONFIG_ZMK_POINTING*` — trackpad/pointing support.

Refer to the upstream ZMK + MoErgo docs for the full set.

### `config/info.json`

QMK-shaped layout description: `layouts.LAYOUT.layout` is a list of `{label, row, col, x, y, r}` entries. Used by:

- The MoErgo Go60 Layout Editor webapp.
- keymap-drawer (via this repo's `draw.sh`).

**Not** read by the firmware build itself — Zephyr derives matrix layout from the board files in upstream ZMK.

### `config/default.nix`

Three things to know:

- Receives `firmware` as an argument (the upstream ZMK `default.nix`'s output). When called without an arg, defaults to `import ../src {}` — hence the `src/` checkout in CI and the `/src` worktree in Docker.
- Calls `firmware.zmk.override { board = "go60_lh"; ... }` and `… "go60_rh"` to build each half.
- Calls `firmware.combine_uf2` to merge both into one UF2.

If you want to tweak Kconfig per-hand (rare — only useful when a feature must differ between halves), this is where you'd do it.

## Iteration tips

- **Edit-build-flash loop**: edit `config/go60.keymap` → `./flash.sh` → keep typing. With the Nix store volume warm and `SKIP_FETCH=1`, full cycle is well under a minute.
- **Pin ZMK**: passing a SHA to `./build.sh <sha>` makes builds reproducible and improves Cachix hit rates (cache is per-derivation, and `main` drifts).
- **Try changes without flashing**: every push generates a downloadable artifact via `build.yml` — useful when iterating on a different machine.
- **Visualize before flashing**: run `./draw.sh` to confirm a layout change looks the way you expect.

## Useful references

- [ZMK Documentation](https://zmk.dev/docs)
- [ZMK Behaviors](https://zmk.dev/docs/keymaps/behaviors)
- [MoErgo ZMK fork](https://github.com/moergo-sc/zmk)
- [MoErgo Go60 Support](https://moergo.com/go60-support)
- [keymap-drawer](https://github.com/caksoylar/keymap-drawer)
