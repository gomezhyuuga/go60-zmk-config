#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

./build.sh "$@"

for drive in /Volumes/GLV80*BOOT; do
    if [ -d "$drive" ]; then
        cp go60.uf2 "$drive/"
        echo "→ flashed to $drive"
        exit 0
    fi
done

echo "No bootloader drive mounted." >&2
echo "Put the keyboard into bootloader mode: hold the magic key + tap the &bootloader key on the Magic layer." >&2
exit 1
