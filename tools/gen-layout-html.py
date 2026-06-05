#!/usr/bin/env python3
"""Generate a self-contained HTML layout viewer from the keymap-drawer sources.

Reads:
  - keymap-drawer/keymap.yaml   (layers + combos, produced by ./draw.sh)
  - config/info.json            (physical key positions, incl. thumb rotation)

Writes:
  - wiki/layout.html            (one page, all layers, JS layer switcher)

Unlike the SVG renderer this handles multi-line legends and CSS styling. Re-run
after editing the keymap (run ./draw.sh first to refresh keymap.yaml).
"""

import json
import html
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEYMAP_YAML = ROOT / "keymap-drawer" / "keymap.yaml"
INFO_JSON = ROOT / "config" / "info.json"
OUT_HTML = ROOT / "wiki" / "layout.html"

# Layers to omit: per-finger HRM helper layers, the mouse speed variants, and Gaming.
# The main Mouse layer is kept.
EXCLUDE = {
    "LeftPinky", "LeftRingy", "LeftMiddy", "LeftIndex",
    "RightPinky", "RightRingy", "RightMiddy", "RightIndex",
    "MouseSlow", "MouseFast", "MouseWarp",
    "Gaming",
}

# Hold legends that name a layer get the "layer" accent.
LAYER_NAMES = {
    "HRM_macOS", "Typing", "Autoshift", "Cursor", "Keypad",
    "Symbol", "Mouse", "Magic", "fn", "Gaming",
}

# Modifier tokens → macOS glyphs (matched case-insensitively). Covers both the
# keymap-drawer prefixes (Gui/Sft/Alt/Ctl) and raw keycodes (LGUI/RSHFT/…).
MOD_SYMBOLS = {
    "GUI": "⌘", "LGUI": "⌘", "RGUI": "⌘", "LG": "⌘", "RG": "⌘", "CMD": "⌘",
    "SFT": "⇧", "SHIFT": "⇧", "LSHFT": "⇧", "RSHFT": "⇧", "LSFT": "⇧", "RSFT": "⇧",
    "ALT": "⌥", "LALT": "⌥", "RALT": "⌥", "OPT": "⌥",
    "CTL": "⌃", "CTRL": "⌃", "LCTRL": "⌃", "RCTRL": "⌃",
}
# Whole-token keys → glyphs.
KEY_SYMBOLS = {
    "TAB": "⇥", "RET": "↩", "ENTER": "↩", "BSPC": "⌫", "DEL": "⌦",
    "ESC": "⎋", "SPACE": "␣", "CAPS": "⇪",
    "LEFT": "←", "RIGHT": "→", "UP": "↑", "DOWN": "↓",
}
HYPER = "⌃⌥⇧⌘"  # Hyper = all four modifiers


def _glyph(token):
    u = token.upper()
    if token == "Hyper":
        return HYPER
    return MOD_SYMBOLS.get(u) or KEY_SYMBOLS.get(u) or token


def symbolize(label):
    """Replace modifier / nav tokens with glyphs. 'Gui+LSHFT' -> '⌘⇧', 'Ctl+TAB' -> '⌃⇥'."""
    if not label:
        return label
    if " " in label:
        tokens = label.split()
        # Home-row-mod holds arrive as "behavior_name MOD" (e.g.
        # "HRM_left_pinky_hold_v1B_TKZ LCTRL"); show just the modifier glyph(s).
        if "_" in tokens[0] and len(tokens) > 1:
            return "".join(_glyph(t) for t in tokens[1:])
        return label  # leave other multi-word labels (KP 7, PG UP, BRI DN, mkp LCLK, …)
    return "".join(_glyph(p) for p in label.split("+"))


def norm(label):
    """Strip the ZMK '&' prefix from raw behaviors keymap-drawer couldn't render."""
    if label.startswith("&"):
        label = label[1:]
    return label


def parse_key(entry):
    """Return dict: {tap, hold, kind} for one keymap-drawer key spec."""
    if entry is None:
        return {"tap": "", "hold": "", "kind": "blank"}
    if isinstance(entry, str):
        if entry == "":
            return {"tap": "", "hold": "", "kind": "blank"}
        return {"tap": symbolize(norm(entry)), "hold": "", "kind": "key"}
    # dict form
    typ = entry.get("type")
    tap = entry.get("t", "")
    hold = entry.get("h", "")
    if typ == "trans":
        return {"tap": tap or "▽", "hold": "", "kind": "trans"}
    if typ == "held":
        return {"tap": symbolize(norm(str(tap))) if tap else "", "hold": "", "kind": "held"}
    # kind is decided on the raw hold (before symbolizing) so layer names still match.
    kind = "key"
    if hold:
        kind = "layer" if hold in LAYER_NAMES else "dual"
    return {
        "tap": symbolize(norm(str(tap))),
        "hold": symbolize(norm(str(hold))),
        "kind": kind,
    }


def main():
    keymap = yaml.safe_load(KEYMAP_YAML.read_text())
    info = json.loads(INFO_JSON.read_text())
    geo = info["layouts"]["LAYOUT"]["layout"]

    layers = {
        name: [parse_key(k) for k in keys]
        for name, keys in keymap["layers"].items()
        if name not in EXCLUDE
    }

    # Physical positions, parallel to each layer's key array.
    keys_geo = [
        {
            "x": g["x"], "y": g["y"],
            "r": g.get("r", 0),
            "rx": g.get("rx", g["x"]), "ry": g.get("ry", g["y"]),
        }
        for g in geo
    ]

    data = {"geo": keys_geo, "layers": layers, "order": list(layers.keys())}
    payload = json.dumps(data, ensure_ascii=False)

    OUT_HTML.write_text(TEMPLATE.replace("/*DATA*/", payload))
    print(f"→ {OUT_HTML.relative_to(ROOT)}  ({len(layers)} layers)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Go60 Layout</title>
<style>
  :root {
    --bg:#0f1115; --panel:#171a21; --key:#232834; --edge:#2e3645;
    --text:#e7ecf3; --muted:#8a93a6;
    --c-layer:#6cc2ff; --c-dual:#ffb454; --c-held:#ff7a93; --c-trans:#3a4150;
    --unit:64px; --keysize:58px;
  }
  * { box-sizing:border-box; }
  body {
    margin:0; color:var(--text);
    font-family:ui-sans-serif,-apple-system,"SF Pro Text","Segoe UI",Roboto,sans-serif;
    background:radial-gradient(1200px 700px at 50% -10%,#1a1f2b,var(--bg));
    padding:24px 16px;
    min-height:100vh;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
  }
  .grid { display:flex; gap:18px 22px; justify-content:center; align-items:flex-start; }
  .slot { display:flex; flex-direction:column; align-items:center; gap:7px; }
  .slot .title {
    display:flex; align-items:center; gap:6px; font-size:12.5px; color:var(--text);
  }
  .slot .title .num {
    display:inline-flex; align-items:center; justify-content:center;
    width:16px; height:16px; border-radius:4px; font-size:10px; font-weight:700;
    background:var(--c-layer); color:#0f1115;
  }
  .board-wrap { position:relative; }
  .board {
    position:absolute; top:0; left:0; transform-origin:top left;
    width:calc(17.7 * var(--unit)); height:calc(6.7 * var(--unit));
  }
  .key {
    position:absolute; width:var(--keysize); height:var(--keysize);
    background:linear-gradient(180deg,var(--key),#1d222c);
    border:2px solid var(--edge); border-radius:8px;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding:3px; text-align:center; overflow:hidden;
    box-shadow:0 2px 0 #00000055, inset 0 1px 0 #ffffff08;
  }
  .key .tap { font-size:12px; font-weight:600; line-height:1.05; word-break:break-word; }
  .key .hold {
    font-size:8.5px; line-height:1.05; margin-top:2px; letter-spacing:.2px;
    color:var(--c-dual); text-transform:uppercase; word-break:break-word;
  }
  .key.layer { border-color:#245067; }
  .key.layer .tap { color:var(--c-layer); }
  .key.layer .hold { color:var(--c-layer); }
  .key.dual { border-color:#5a4524; }
  .key.held { border-color:var(--c-held); box-shadow:0 0 0 1px var(--c-held) inset, 0 2px 0 #00000055; }
  .key.held .tap { color:var(--c-held); }
  .key.trans { opacity:.32; }
  .key.trans .tap { color:var(--muted); font-weight:400; }
  .key.blank { opacity:.5; }
  .pos { position:absolute; top:2px; right:4px; font-size:7px; color:#475061; }

  .navbar {
    margin:20px auto 0; display:flex; flex-wrap:nowrap;
    gap:4px; justify-content:center;
  }
  .nav {
    display:flex; align-items:center; gap:5px; cursor:pointer; white-space:nowrap;
    background:var(--panel); border:1px solid var(--edge); border-radius:7px;
    padding:3px 8px 3px 4px; font-size:11px; color:var(--muted); transition:.12s;
  }
  .nav:hover { color:var(--text); border-color:#3a4456; }
  .nav.active { background:#26354a; border-color:var(--c-layer); color:#dff0ff; }
  .nav .num {
    display:inline-flex; align-items:center; justify-content:center;
    width:15px; height:15px; border-radius:4px; font-size:10px; font-weight:700;
    background:#00000040; color:var(--c-layer);
  }
  .nav.active .num { background:var(--c-layer); color:#0f1115; }

  footer {
    margin-top:22px; max-width:780px; display:flex; flex-direction:column;
    align-items:center; gap:8px; font-size:12px; color:var(--muted);
  }
  footer .row { display:flex; flex-wrap:wrap; gap:7px 18px; justify-content:center; }
  footer .item { display:flex; align-items:center; gap:6px; }
  footer .sw { width:11px; height:11px; border-radius:3px; display:inline-block; }
  footer kbd {
    font-family:inherit; font-size:11px; color:var(--text);
    background:#00000040; border:1px solid var(--edge);
    border-radius:5px; padding:1px 6px;
  }
  footer .gen { font-size:10.5px; color:#4d566a; margin-top:2px; }
</style>
</head>
<body>
<div class="grid" id="grid"></div>

<div class="navbar" id="navbar"></div>

<footer>
  <div class="row">
    <span class="item"><span class="sw" style="background:var(--c-layer)"></span> Layer switch</span>
    <span class="item"><span class="sw" style="background:var(--c-dual)"></span> Hold = modifier</span>
    <span class="item"><span class="sw" style="background:var(--c-held)"></span> Held key</span>
    <span class="item"><span class="sw" style="background:var(--c-trans)"></span> ▽ transparent</span>
    <span class="item">⌘ Cmd · ⌥ Opt · ⇧ Shift · ⌃ Ctrl</span>
  </div>
  <div class="row">
    <kbd>Tab</kbd> show <b id="modecount">1</b> / 2 / 4 layers
    <kbd>←</kbd> <kbd>→</kbd> move
    <kbd>1</kbd>–<kbd>9</kbd> jump to layer
  </div>
  <div class="gen">Generated from <code>keymap-drawer/keymap.yaml</code> + <code>config/info.json</code> by <code>tools/gen-layout-html.py</code></div>
</footer>

<script>
const DATA = /*DATA*/;
const UNIT = 64, KEY = 58;
const W = 17.7 * UNIT, H = 6.7 * UNIT;
const N = DATA.order.length;

// Tab cycles how many layers are shown at once.
const MODES = [
  { count: 1, scale: 1.00, cols: 1 },
  { count: 2, scale: 0.55, cols: 2 },  // side by side
  { count: 4, scale: 0.50, cols: 2 },  // 2x2
];
let modeIdx = 0;
let current = 0;

const grid = document.getElementById("grid");
const navbar = document.getElementById("navbar");
const modecount = document.getElementById("modecount");

DATA.order.forEach((name, i) => {
  const n = document.createElement("div");
  n.className = "nav";
  n.innerHTML = `<span class="num">${i + 1}</span>${esc(name)}`;
  n.onclick = () => { current = i; render(); };
  navbar.appendChild(n);
});

function esc(s){ const d=document.createElement("div"); d.textContent=s; return d.innerHTML; }

function buildBoard(layerIdx) {
  const board = document.createElement("div");
  board.className = "board";
  DATA.layers[DATA.order[layerIdx]].forEach((k, idx) => {
    const g = DATA.geo[idx];
    const el = document.createElement("div");
    el.className = "key " + k.kind;
    el.style.left = (g.x * UNIT) + "px";
    el.style.top  = (g.y * UNIT) + "px";
    if (g.r) {
      el.style.transformOrigin = ((g.rx - g.x) * UNIT) + "px " + ((g.ry - g.y) * UNIT) + "px";
      el.style.transform = "rotate(" + g.r + "deg)";
    }
    let inner = "";
    if (k.tap) inner += `<div class="tap">${esc(k.tap)}</div>`;
    if (k.hold) inner += `<div class="hold">${esc(k.hold)}</div>`;
    inner += `<span class="pos">${idx}</span>`;
    el.innerHTML = inner;
    board.appendChild(el);
  });
  return board;
}

function render() {
  const m = MODES[modeIdx];
  modecount.textContent = m.count;
  grid.style.flexWrap = m.cols === 1 ? "nowrap" : "wrap";
  grid.style.flexDirection = m.cols === 1 ? "column" : "row";
  grid.style.maxWidth = m.cols === 1 ? "none" : (W * m.scale * m.cols + 40) + "px";

  grid.innerHTML = "";
  const visible = new Set();
  for (let j = 0; j < m.count; j++) {
    const li = (current + j) % N;
    visible.add(li);

    const slot = document.createElement("div");
    slot.className = "slot";

    const title = document.createElement("div");
    title.className = "title";
    title.innerHTML = `<span class="num">${li + 1}</span>${esc(DATA.order[li])}`;

    const wrap = document.createElement("div");
    wrap.className = "board-wrap";
    wrap.style.width = (W * m.scale) + "px";
    wrap.style.height = (H * m.scale) + "px";

    const board = buildBoard(li);
    board.style.transform = "scale(" + m.scale + ")";
    wrap.appendChild(board);

    slot.appendChild(title);
    slot.appendChild(wrap);
    grid.appendChild(slot);
  }
  [...navbar.children].forEach((t, j) => t.classList.toggle("active", visible.has(j)));
}

document.addEventListener("keydown", e => {
  if (e.key === "Tab") {
    e.preventDefault();
    modeIdx = (modeIdx + 1) % MODES.length;
    render();
  } else if (e.key === "ArrowRight") {
    current = (current + 1) % N; render();
  } else if (e.key === "ArrowLeft") {
    current = (current - 1 + N) % N; render();
  } else if (e.key >= "1" && e.key <= "9") {
    const idx = parseInt(e.key, 10) - 1;
    if (idx < N) { current = idx; render(); }
  }
});

render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
