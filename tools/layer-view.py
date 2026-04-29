#!/usr/bin/env python3
"""Interactive terminal viewer for keymap layer SVGs.

Renders each SVG in `keymap-drawer/layers/` via `kitten icat` and lets you flip
between layers with single-key navigation. Stdlib only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import termios
import tty
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = REPO_ROOT / "keymap-drawer" / "layers"

CLEAR = "\x1b[2J\x1b[H"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"


def read_key() -> str:
    """Read a single keypress, including escape sequences like arrow keys."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1).decode(errors="replace")
        if ch == "\x1b":
            # Try to read a CSI sequence non-blockingly-ish.
            try:
                rest = os.read(fd, 2).decode(errors="replace")
            except OSError:
                rest = ""
            return ch + rest
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def render(svg: Path, idx: int, total: int) -> None:
    cols, _ = shutil.get_terminal_size((100, 40))
    header = f"[{idx + 1}/{total}] {svg.stem}   (j/k next/prev, g/G first/last, 1-9 jump, r reload, q quit)"
    sys.stdout.write(CLEAR)
    sys.stdout.write(header[:cols] + "\n")
    sys.stdout.flush()
    subprocess.run(["kitten", "icat", str(svg)], check=False)
    sys.stdout.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_DIR,
        help=f"directory of SVGs (default: {DEFAULT_DIR})",
    )
    args = ap.parse_args()

    if not shutil.which("kitten"):
        print("kitten not found. Install Kitty terminal.", file=sys.stderr)
        return 1

    svgs = sorted(args.dir.glob("*.svg"))
    if not svgs:
        print(f"no SVGs in {args.dir}", file=sys.stderr)
        return 1

    idx = 0
    sys.stdout.write(HIDE_CURSOR)
    try:
        render(svgs[idx], idx, len(svgs))
        while True:
            key = read_key()
            if key in ("q", "\x03", "\x1b"):
                break
            elif key in ("j", "n", " ", "\x1b[C"):
                idx = min(idx + 1, len(svgs) - 1)
            elif key in ("k", "p", "\x1b[D"):
                idx = max(idx - 1, 0)
            elif key == "g":
                idx = 0
            elif key == "G":
                idx = len(svgs) - 1
            elif key == "r":
                pass
            elif key.isdigit() and key != "0":
                target = int(key) - 1
                if target < len(svgs):
                    idx = target
                else:
                    continue
            else:
                continue
            render(svgs[idx], idx, len(svgs))
    finally:
        sys.stdout.write(SHOW_CURSOR + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
