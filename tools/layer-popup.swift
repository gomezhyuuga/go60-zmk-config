import Cocoa
import WebKit

class KeyCaptureWindow: NSWindow {
    override var canBecomeKey: Bool { true }

    override func keyDown(with event: NSEvent) {
        if event.keyCode == 53 { NSApp.terminate(nil) } // Escape
        else { super.keyDown(with: event) }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!

    func applicationDidFinishLaunching(_ notification: Notification) {
        let layersDir = resolveLayersDir()
        let html = buildHTML(layersDir: layersDir)

        let screen = NSScreen.main!.visibleFrame
        window = KeyCaptureWindow(
            contentRect: screen,
            styleMask: [.titled, .closable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.title = "Keyboard Layers"
        window.titlebarAppearsTransparent = true
        window.backgroundColor = NSColor(red: 0.07, green: 0.07, blue: 0.07, alpha: 1)

        let webView = WKWebView(frame: window.contentView!.bounds)
        webView.autoresizingMask = [.width, .height]
        webView.loadHTMLString(html, baseURL: nil)
        window.contentView!.addSubview(webView)

        window.setFrame(screen, display: true)
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool {
        true
    }

    private func resolveLayersDir() -> String {
        if let env = ProcessInfo.processInfo.environment["U_KBD_KEYMAP"] {
            return env
        }
        let binary = URL(fileURLWithPath: CommandLine.arguments[0])
        return binary.deletingLastPathComponent()
            .appendingPathComponent("../keymap-drawer/layers")
            .standardized.path
    }

    private func buildHTML(layersDir: String) -> String {
        let fm = FileManager.default
        let files = (try? fm.contentsOfDirectory(atPath: layersDir))?
            .filter { $0.hasSuffix(".svg") }
            .sorted() ?? []

        var layerData = "["
        for file in files {
            let name = String(file.dropLast(4))
            let path = "\(layersDir)/\(file)"
            guard var svg = try? String(contentsOfFile: path, encoding: .utf8) else { continue }
            svg = svg.replacingOccurrences(
                of: #"<svg width="\d+" height="\d+""#,
                with: "<svg",
                options: .regularExpression
            )
            // Escape backticks so it's safe inside a JS template literal
            let escapedSVG = svg.replacingOccurrences(of: "`", with: "\\`")
            layerData += "{name:`\(name)`,svg:`\(escapedSVG)`},"
        }
        layerData += "]"

        return """
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          html, body { height: 100%; }
          body {
            background: #111;
            color: #ccc;
            font-family: -apple-system, sans-serif;
            display: flex;
            flex-direction: column;
            overflow: hidden;
          }
          #main {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-height: 0;
          }
          #sidebar {
            flex-shrink: 0;
            background: #0d0d0f;
            border-top: 1px solid #222;
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            padding: 10px 12px;
            gap: 4px 2px;
          }
          .sidebar-item {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            cursor: pointer;
            border-radius: 6px;
            transition: background 0.1s;
          }
          .sidebar-item:hover { background: #1a1a1c; }
          .sidebar-item.active { background: #2a2a2e; }
          .sidebar-num {
            font-size: 14px;
            font-weight: 700;
            color: #444;
            flex-shrink: 0;
          }
          .sidebar-item.active .sidebar-num { color: #888; }
          .sidebar-name {
            font-size: 14px;
            color: #666;
          }
          .sidebar-item.active .sidebar-name { color: #ddd; }
          #nav {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            padding: 8px 16px;
            font-size: 12px;
            color: #555;
            flex-shrink: 0;
          }
          #counter { color: #888; font-weight: 600; min-width: 80px; text-align: center; }
          #mode-label { color: #666; font-weight: 600; min-width: 36px; text-align: center; }
          #viewport {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 0 14px 14px;
            min-height: 0;
          }
          #panels {
            display: grid;
            gap: 12px;
            width: 100%;
            height: 100%;
            align-content: center;
          }
          .panel {
            background: #1c1c1e;
            border-radius: 8px;
            padding: 10px 12px 12px;
            display: flex;
            flex-direction: column;
            min-height: 0;
          }
          .label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 6px;
            flex-shrink: 0;
          }
          .panel svg { width: 100%; height: auto; display: block; }
          #panels.fill-height { height: 100%; }
          #panels.fill-height .panel { height: 100%; justify-content: center; }
          #panels.fill-height .panel svg { height: 100%; width: auto; max-width: 100%; }
        </style>
        </head>
        <body>
          <div id="main">
            <div id="nav">
              <span>← →  navigate</span>
              <span id="counter"></span>
              <span id="mode-label"></span>
              <span>tab  layout &nbsp; esc  close</span>
            </div>
            <div id="viewport">
              <div id="panels"></div>
            </div>
          </div>
          <div id="sidebar"></div>
        <script>
          const layers = \(layerData);

          const MODES = [
            { label: '2×2', cols: 2, perPage: 4 },
            { label: '1×2', cols: 2, perPage: 2 },
            { label: '1×1', cols: 1, perPage: 1 },
          ];
          let modeIdx = 0;
          let idx = 0;

          function displayName(name) {
            return name.replace(/^\\d+_/, '');
          }

          function jumpTo(n) {
            const m = MODES[modeIdx];
            const max = layers.length - m.perPage;
            idx = Math.max(0, Math.min(n, max));
            render();
          }

          function renderSidebar() {
            const m = MODES[modeIdx];
            const sidebar = document.getElementById('sidebar');
            sidebar.innerHTML = layers.map((l, i) => {
              const active = i >= idx && i < idx + m.perPage ? 'active' : '';
              return `<div class="sidebar-item ${active}" onclick="jumpTo(${i})">
                <span class="sidebar-num">${i + 1}</span>
                <span class="sidebar-name">${displayName(l.name)}</span>
              </div>`;
            }).join('');
          }

          function render() {
            const m = MODES[modeIdx];
            const total = layers.length;
            const visible = layers.slice(idx, idx + m.perPage);

            const panels = document.getElementById('panels');
            panels.style.gridTemplateColumns = `repeat(${m.cols}, 1fr)`;

            const fill = m.cols === 1;
            panels.classList.toggle('fill-height', fill);
            panels.style.margin = fill ? '0 auto' : '';

            panels.innerHTML = visible.map(l =>
              `<div class="panel"><div class="label">${displayName(l.name)}</div>${l.svg}</div>`
            ).join('');

            const end = Math.min(idx + m.perPage, total);
            document.getElementById('counter').textContent = `${idx + 1}–${end} / ${total}`;
            document.getElementById('mode-label').textContent = m.label;

            renderSidebar();
          }

          function navigate(delta) {
            const m = MODES[modeIdx];
            const max = layers.length - m.perPage;
            idx = Math.max(0, Math.min(idx + delta, max));
            render();
          }

          function cycleMode() {
            modeIdx = (modeIdx + 1) % MODES.length;
            idx = 0;
            render();
          }

          render();

          document.addEventListener('keydown', e => {
            if (e.key === 'ArrowRight') { navigate(1);  e.preventDefault(); }
            if (e.key === 'ArrowLeft')  { navigate(-1); e.preventDefault(); }
            if (e.key === 'Tab')        { cycleMode();  e.preventDefault(); }
            const n = parseInt(e.key);
            if (!isNaN(n) && n >= 1 && n <= layers.length) {
              jumpTo(n - 1);
              e.preventDefault();
            }
          });
        </script>
        </body>
        </html>
        """
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.regular)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
