#!/bin/bash

set -euo pipefail

IMAGE=go60-zmk-config-docker
VOLUME=go60-zmk-nix-store
BRANCH="${1:-main}"

# Rebuild image only when missing, or when REBUILD=1 is passed.
if [ "${REBUILD:-0}" = "1" ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    docker build -t "$IMAGE" .
fi

docker run --rm \
    -v "$PWD:/config" \
    -v "$VOLUME:/nix" \
    -e UID="$(id -u)" -e GID="$(id -g)" \
    -e BRANCH="$BRANCH" \
    -e SKIP_FETCH="${SKIP_FETCH:-0}" \
    "$IMAGE"
