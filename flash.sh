#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

WAIT_SECONDS="${WAIT_SECONDS:-15}"

./build.sh "$@"

echo "Waiting up to ${WAIT_SECONDS}s for a Go60 bootloader drive to mount..."
echo "  Put the keyboard into bootloader mode: hold the magic key + tap the &bootloader key on the Magic layer."

deadline=$(( $(date +%s) + WAIT_SECONDS ))
while [ "$(date +%s)" -lt "$deadline" ]; do
    for drive in /Volumes/GO60*BOOT; do
        if [ -d "$drive" ]; then
						echo "Device found: $drive"
            # Stream bytes rather than `cp` — avoids macOS metadata-preserve
            # issues on the bootloader's FAT filesystem.
            if cat go60.uf2 > "$drive/go60.uf2" 2>/dev/null; then
                echo "→ flashed to $drive"
                exit 0
            fi
            cat <<EOF >&2
Permission denied writing to $drive.
On macOS, grant your terminal access to removable volumes:
  System Settings → Privacy & Security → Files and Folders
  (or "Removable Volumes") → enable for your terminal app.
Then re-run: make flash
EOF
            exit 1
        fi
    done
    sleep 1
done

echo "No bootloader drive mounted within ${WAIT_SECONDS}s." >&2
exit 1
