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

echo "→ $OUT/keymap.yaml"

# One SVG per layer, into keymap-drawer/layers/.
LAYER_DIR="$OUT/layers"
mkdir -p "$LAYER_DIR"
rm -f "$LAYER_DIR"/*.svg

# Skip per-finger HRM helper layers, autoshift, and the Mouse{Slow,Fast,Warp} variants.
SKIP_RE='(Pinky|Middy|Index|Ringy)$|^Autoshift$|^Mouse(Slow|Fast|Warp)$'

# Layer names are the top-level keys under `layers:` in the yaml.
idx=0
while read -r layer; do
    [ -z "$layer" ] && continue
    if [[ "$layer" =~ $SKIP_RE ]]; then
        echo "  skip $layer"
        continue
    fi
    name="$(printf '%02d' $idx)_${layer}"
    keymap draw -s "$layer" -- "$OUT/keymap.yaml" > "$LAYER_DIR/$name.svg" < /dev/null
    echo "→ $LAYER_DIR/$name.svg"
    idx=$((idx + 1))
done < <(python3 -c "
import yaml
with open('$OUT/keymap.yaml') as f: d = yaml.safe_load(f)
print('\n'.join(d.get('layers', {}).keys()))
")
