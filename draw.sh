#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v keymap >/dev/null 2>&1; then
    echo "keymap-drawer not found. Install it with:" >&2
    echo "  pipx install keymap-drawer" >&2
    echo "or:" >&2
    echo "  pip install --user keymap-drawer" >&2
    exit 1
fi

OUT=keymap-drawer
mkdir -p "$OUT"

# Parse the ZMK keymap and prepend the physical layout from info.json.
# We strip any auto-detected `layout:` line so the Go60 physical layout wins.
{
    echo 'layout: {qmk_info_json: config/info.json}'
    keymap parse -z config/go60.keymap | grep -v '^layout:'
} > "$OUT/keymap.yaml"

keymap draw "$OUT/keymap.yaml" > "$OUT/keymap.svg"

echo "→ $OUT/keymap.yaml"
echo "→ $OUT/keymap.svg"
