#!/usr/bin/env python3
"""Identify which Go60 matrix POS_* a keypress came from, and show the
binding from a chosen layer next to each position.

Reads:
  - config/go60.keymap   — for `#define POS_<name> <idx>` mapping
  - config/info.json     — MoErgo Layout Editor export with per-layer bindings

POSIX-only (macOS, Linux). Stdlib only. Press 'q' or Ctrl-C to quit.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import select
import sys
import termios
import tty
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYMAP = ROOT / "config" / "go60.keymap"
INFO = ROOT / "config" / "info.json"

# byte / escape-sequence -> POS_* (matches the codeToPos map in key-id.html)
CHAR_TO_POS: dict[str, str] = {
    "=": "LH_C6R1",
    "1": "LH_C5R1", "2": "LH_C4R1", "3": "LH_C3R1", "4": "LH_C2R1", "5": "LH_C1R1",
    "6": "RH_C1R1", "7": "RH_C2R1", "8": "RH_C3R1", "9": "RH_C4R1", "0": "RH_C5R1",
    "-": "RH_C6R1",
    "\t": "LH_C6R2",
    "q": "LH_C5R2", "w": "LH_C4R2", "e": "LH_C3R2", "r": "LH_C2R2", "t": "LH_C1R2",
    "y": "RH_C1R2", "u": "RH_C2R2", "i": "RH_C3R2", "o": "RH_C4R2", "p": "RH_C5R2",
    "\\": "RH_C6R2",
    "\x1b": "LH_C6R3",
    "a": "LH_C5R3", "s": "LH_C4R3", "d": "LH_C3R3", "f": "LH_C2R3", "g": "LH_C1R3",
    "h": "RH_C1R3", "j": "RH_C2R3", "k": "RH_C3R3", "l": "RH_C4R3", ";": "RH_C5R3",
    "'": "RH_C6R3", '"': "RH_C6R3",
    "z": "LH_C5R4", "x": "LH_C4R4", "c": "LH_C3R4", "v": "LH_C2R4", "b": "LH_C1R4",
    "n": "RH_C1R4", "m": "RH_C2R4", ",": "RH_C3R4", ".": "RH_C4R4", "/": "RH_C5R4",
    " ": "LT_T3", "\r": "RT_T2", "\x7f": "LT_T1",
}

SHIFT_NORMALIZE: dict[str, str] = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
    "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
    "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
    ":": ";", "<": ",", ">": ".", "?": "/", "~": "`",
}

# Map ZMK keycode names → terse 1-3 char labels for the cell display.
KEY_DISPLAY = {
    "EQUAL": "=", "MINUS": "-", "BSLH": "\\", "FSLH": "/",
    "SEMI": ";", "SQT": "'", "DQT": '"', "GRAVE": "`",
    "COMMA": ",", "DOT": ".", "LBKT": "[", "RBKT": "]",
    "LBRC": "{", "RBRC": "}", "LPAR": "(", "RPAR": ")",
    "EXCL": "!", "AT": "@", "HASH": "#", "DLLR": "$",
    "PRCNT": "%", "CARET": "^", "AMPS": "&", "STAR": "*",
    "UNDER": "_", "PLUS": "+", "TILDE": "~", "QMARK": "?",
    "SPACE": "Spc", "RET": "Ret", "ENTER": "Ret", "TAB": "Tab",
    "ESC": "Esc", "BSPC": "Bsp", "DEL": "Del", "INS": "Ins",
    "LSHFT": "Lsh", "RSHFT": "Rsh", "LSHIFT": "Lsh", "RSHIFT": "Rsh",
    "LCTRL": "Lct", "RCTRL": "Rct", "LALT": "Lal", "RALT": "Ral",
    "LGUI": "Lgu", "RGUI": "Rgu",
    "UP": "↑", "DOWN": "↓", "LEFT": "←", "RIGHT": "→",
    "HOME": "Hom", "END": "End", "PG_UP": "PgU", "PG_DN": "PgD",
    "CAPS": "Cap", "SLCK": "Slk", "PSCRN": "PSc", "PAUSE_BREAK": "Pau",
    "K_APP": "App",
    "C_MUTE": "Mut", "C_VOL_UP": "V+", "C_VOL_DN": "V-",
    "C_PP": "PP", "C_NEXT": ">>", "C_PREV": "<<",
    "C_BRI_UP": "B+", "C_BRI_DN": "B-",
    "KP_N0": "0", "KP_N1": "1", "KP_N2": "2", "KP_N3": "3", "KP_N4": "4",
    "KP_N5": "5", "KP_N6": "6", "KP_N7": "7", "KP_N8": "8", "KP_N9": "9",
    "KP_DOT": ".", "KP_PLUS": "+", "KP_MINUS": "-", "KP_SLASH": "/",
    "KP_MULTIPLY": "*", "KP_ENTER": "Ret", "KP_EQUAL": "=", "KP_NUM": "Num",
}


def short_keycode(name: str) -> str:
    """Render a ZMK keycode label in <=4 chars."""
    if name in KEY_DISPLAY:
        return KEY_DISPLAY[name]
    if re.fullmatch(r"N\d", name):       # N0..N9 → 0..9
        return name[1:]
    if re.fullmatch(r"F\d{1,2}", name):  # F1..F24 stay
        return name
    if len(name) == 1:
        return name
    # LS(X), LC(X), LA(X), LG(X) — modifier-wrapped keycodes
    m = re.fullmatch(r"L([SCAG])\((.+)\)", name)
    if m:
        mod = {"S": "S", "C": "C", "A": "A", "G": "G"}[m.group(1)]
        return f"{mod}-{short_keycode(m.group(2))}"
    return name[:4]


def param_to_str(p) -> str:
    """Flatten a possibly-nested param dict into a keycode string,
    e.g. {value: 'LS', params: [{value: 'SEMI'}]} -> 'LS(SEMI)'."""
    if isinstance(p, dict):
        v = str(p.get("value", ""))
        inner = p.get("params") or []
        if inner:
            return f"{v}({','.join(param_to_str(x) for x in inner)})"
        return v
    return str(p)


def format_binding(b: dict) -> str:
    """Compress a layer binding into a 5-char-or-shorter cell label."""
    if not isinstance(b, dict):
        return "?"
    val = b.get("value", "")
    params = [param_to_str(p) for p in b.get("params", [])]

    if val == "&trans":
        return "▽"
    if val in ("&none", ""):
        return "·"
    if val == "&kp" and params:
        return short_keycode(params[0])
    if val == "&mo" and params:
        return f"mo{params[0].split('_')[-1][:3]}"
    if val == "&to" and params:
        return f"→{params[0].split('_')[-1][:3]}"
    if val in ("&mt", "&tp", "&hm", "&hml", "&hmr") and len(params) >= 2:
        return short_keycode(params[1])  # tap value
    if val == "&sk" and params:
        return f"·{short_keycode(params[0])}"
    if val == "&bt" and params:
        return f"BT{params[1]}" if len(params) >= 2 else "BT"
    if val == "&out" and params:
        return params[0].replace("OUT_", "")[:4]
    if val == "&rgb_ug" and params:
        return f"rgb"
    if val == "&caps_word":
        return "CW"
    if val == "&bootloader":
        return "Boot"
    if val == "&sys_reset":
        return "Rst"
    # Generic hold-tap / HRM family: <behavior> MOD TAP — show tap (last param).
    if params:
        return short_keycode(params[-1])
    # Fall back to the behavior's short name.
    return val.lstrip("&")[:4]


def parse_pos_defines(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    pat = re.compile(r"^#define\s+POS_(\S+)\s+(\d+)\s*$")
    for line in path.read_text().splitlines():
        m = pat.match(line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


# Visible grid: list of rows; each row is a list of (POS-name | None, fallback-glyph).
# Glyph is the original Base-layer hint, used only when no info.json is loaded.
ROWS: list[list[tuple[str | None, str]]] = [
    [("LH_C6R1", "="), ("LH_C5R1", "1"), ("LH_C4R1", "2"), ("LH_C3R1", "3"), ("LH_C2R1", "4"), ("LH_C1R1", "5"),
     ("RH_C1R1", "6"), ("RH_C2R1", "7"), ("RH_C3R1", "8"), ("RH_C4R1", "9"), ("RH_C5R1", "0"), ("RH_C6R1", "-")],
    [("LH_C6R2", "Tab"), ("LH_C5R2", "Q"), ("LH_C4R2", "W"), ("LH_C3R2", "E"), ("LH_C2R2", "R"), ("LH_C1R2", "T"),
     ("RH_C1R2", "Y"), ("RH_C2R2", "U"), ("RH_C3R2", "I"), ("RH_C4R2", "O"), ("RH_C5R2", "P"), ("RH_C6R2", "\\")],
    [("LH_C6R3", "Esc"), ("LH_C5R3", "A"), ("LH_C4R3", "S"), ("LH_C3R3", "D"), ("LH_C2R3", "F"), ("LH_C1R3", "G"),
     ("RH_C1R3", "H"), ("RH_C2R3", "J"), ("RH_C3R3", "K"), ("RH_C4R3", "L"), ("RH_C5R3", ";"), ("RH_C6R3", "'")],
    [("LH_C6R4", "Mag"), ("LH_C5R4", "Z"), ("LH_C4R4", "X"), ("LH_C3R4", "C"), ("LH_C2R4", "V"), ("LH_C1R4", "B"),
     ("RH_C1R4", "N"), ("RH_C2R4", "M"), ("RH_C3R4", ","), ("RH_C4R4", "."), ("RH_C5R4", "/"), ("RH_C6R4", "Kpd")],
    # R5: 3 left-side small keys, gap, 3 right-side small keys
    [(None, ""), (None, ""), ("LH_C4R5", "`"), ("LH_C3R5", "Del"), ("LH_C2R5", "Bsp"),
     (None, ""), (None, ""), ("RH_C2R5", "Gui"), ("RH_C3R5", "["), ("RH_C4R5", "]"),
     (None, ""), (None, "")],
]
# Thumbs displayed left-to-right: outer→inner on left, inner→outer on right.
THUMBS: list[tuple[str, str]] = [
    ("LH_T3", "T3"), ("LH_T2", "T2"), ("LH_T1", "T1"),
    ("RH_T1", "T1"), ("RH_T2", "T2"), ("RH_T3", "T3"),
]

# ANSI
HOME = "\x1b[H"
CLR = "\x1b[2J\x1b[H"
EL = "\x1b[K"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
INV = "\x1b[7m"
CYAN = "\x1b[36m"
PINK = "\x1b[95m"
YEL = "\x1b[33m"
RST = "\x1b[0m"

CELL_W = 6
GAP = "  "


def cell(label: str, hit: bool) -> str:
    s = label[:CELL_W].center(CELL_W)
    if hit:
        return f"{INV}{BOLD}{s}{RST}"
    return f"{s}"


def render(state: dict, last_pos: str | None, last_repr: str) -> str:
    out: list[str] = [HOME]
    layer = state["layer_name"]
    layers = state["all_layers"]
    out.append(f"{BOLD}Go60 Key Identifier{RST}{DIM} — press a key, 'q' to quit{RST}{EL}")
    out.append(f"{DIM}Layer:{RST} {YEL}{layer}{RST}  {DIM}({state['layer_idx'] + 1}/{len(layers)}){RST}{EL}")
    out.append(f"{DIM}{'─' * 78}{RST}{EL}")
    if last_pos:
        out.append(f"Last: {CYAN}{BOLD}POS_{last_pos}{RST}   {DIM}{last_repr}{RST}{EL}")
    elif last_repr:
        out.append(f"Last: {PINK}unmapped{RST}   {DIM}{last_repr}{RST}{EL}")
    else:
        out.append(f"{DIM}Press a key on the Go60…{RST}{EL}")
    out.append(EL)

    cells = state["cells"]
    for row in ROWS:
        left_parts, right_parts = [], []
        for i, (pos, fallback) in enumerate(row):
            label = "" if pos is None else cells.get(pos, fallback)
            (left_parts if i < 6 else right_parts).append(cell(label, pos == last_pos))
        out.append(f"  {''.join(left_parts)}{GAP}{''.join(right_parts)}{EL}")
    out.append(EL)
    pad = " " * (2 + CELL_W * 3)
    thumbs_l = "".join(cell(cells.get(p, fb), p == last_pos) for p, fb in THUMBS[:3])
    thumbs_r = "".join(cell(cells.get(p, fb), p == last_pos) for p, fb in THUMBS[3:])
    out.append(f"{pad}{thumbs_l}{GAP}{thumbs_r}{EL}")
    out.append(EL)
    out.append(f"{DIM}Tip: home-row mods / layer / mouse / bootloader keys won't surface here.{RST}{EL}")
    out.append(f"{DIM}     Use --layer NAME to view a different layer's labels.{RST}{EL}")
    return "\n".join(out)


def read_key(fd: int) -> str:
    ch = os.read(fd, 1).decode("utf-8", errors="replace")
    if ch != "\x1b":
        return ch
    rdy, _, _ = select.select([fd], [], [], 0.05)
    if not rdy:
        return "\x1b"
    seq = ch
    while True:
        rdy, _, _ = select.select([fd], [], [], 0.01)
        if not rdy:
            return seq
        seq += os.read(fd, 1).decode("utf-8", errors="replace")
        if len(seq) > 8:
            return seq


def lookup(key: str) -> str | None:
    if key in CHAR_TO_POS:
        return CHAR_TO_POS[key]
    if len(key) == 1 and key.lower() in CHAR_TO_POS:
        return CHAR_TO_POS[key.lower()]
    if key in SHIFT_NORMALIZE:
        return CHAR_TO_POS.get(SHIFT_NORMALIZE[key])
    return None


def describe(key: str) -> str:
    if len(key) == 1:
        cp = ord(key)
        if 0x20 <= cp < 0x7f:
            return f"{key!r} / 0x{cp:02x}"
        names = {"\t": "Tab", "\r": "Enter", "\n": "Enter",
                 "\x7f": "Backspace", "\x1b": "Esc", " ": "Space"}
        if key in names:
            return f"{names[key]} / 0x{cp:02x}"
        return f"ctrl 0x{cp:02x}"
    return f"sequence {key!r}"


def build_cells(info_layer: list[dict] | None, pos_to_idx: dict[str, int]) -> dict[str, str]:
    cells: dict[str, str] = {}
    if info_layer is None:
        return cells
    for pos, idx in pos_to_idx.items():
        if 0 <= idx < len(info_layer):
            cells[pos] = format_binding(info_layer[idx])
    return cells


def main() -> int:
    ap = argparse.ArgumentParser(description="Identify Go60 key positions and show layer bindings.")
    ap.add_argument("--layer", help="Layer name to display (default: first layer).")
    ap.add_argument("--list-layers", action="store_true", help="List available layers and exit.")
    args = ap.parse_args()

    pos_to_idx: dict[str, int] = {}
    if KEYMAP.exists():
        pos_to_idx = parse_pos_defines(KEYMAP)
    else:
        print(f"warning: {KEYMAP} not found — position labels won't resolve to indices",
              file=sys.stderr)

    info = None
    if INFO.exists():
        try:
            info = json.loads(INFO.read_text())
        except json.JSONDecodeError as e:
            print(f"warning: failed to parse {INFO}: {e}", file=sys.stderr)

    layer_names: list[str] = (info or {}).get("layer_names", []) if info else []
    if args.list_layers:
        for i, n in enumerate(layer_names):
            print(f"{i:2d}  {n}")
        return 0

    layer_idx = 0
    if args.layer:
        if args.layer not in layer_names:
            print(f"error: layer {args.layer!r} not found. Available: {', '.join(layer_names) or '(none)'}",
                  file=sys.stderr)
            return 2
        layer_idx = layer_names.index(args.layer)

    layer_data = info["layers"][layer_idx] if (info and layer_names) else None
    cells = build_cells(layer_data, pos_to_idx)

    state = {
        "cells": cells,
        "layer_idx": layer_idx,
        "layer_name": layer_names[layer_idx] if layer_names else "(no info.json)",
        "all_layers": layer_names or ["(none)"],
    }

    if not sys.stdin.isatty():
        print("error: stdin is not a tty", file=sys.stderr)
        return 2

    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        sys.stdout.write(CLR)
        sys.stdout.write(render(state, None, ""))
        sys.stdout.flush()
        last_pos: str | None = None
        last_repr = ""
        while True:
            try:
                key = read_key(fd)
            except (KeyboardInterrupt, EOFError):
                break
            if key in ("q", "\x03"):
                break
            last_pos = lookup(key)
            last_repr = describe(key)
            sys.stdout.write(render(state, last_pos, last_repr))
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        sys.stdout.write("\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
