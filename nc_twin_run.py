# nc_gui_host.py — NC GUI Host (supports HTML + CSS + JS + SVG via QtWebEngine)
# Runs nc_console.py and renders __TWIN__ commands as real windows (PySide6).
#
# Supports:
# - __TWIN__ + base64(json)  (t_windows format)
# - __TWIN__ + {json}        (plain json)
#
# Renders:
# - window.open / create / window
# - plot.add
# - table.set
# - t_windows: action=create/close/msgbox/init (+ content_html rendered)
#
# NEW (this version):
# - HTML tab gets a JS bridge (QtWebChannel) so JS can send messages to the Log tab:
#     ncSend("hello")  -> shows up as [js] hello
# - Optional per-window CSS + JS injection:
#     content_css, content_js
# - Optional command to run JS on the currently loaded HTML:
#     cmd/action: "html.eval" (or "js.eval") with field: code
#
# NOTE:
# - If QtWebEngine is not installed, HTML falls back to QTextEdit.setHtml() (no JS).
#   Install typically: pip install PySide6 PySide6-QtWebEngine

from __future__ import annotations

import os
import sys
import json
import base64

from PySide6.QtCore import Qt, QProcess, QTimer, QRectF, QCoreApplication, QObject, Signal, Slot
from PySide6.QtGui import QPainter, QPen, QColor

# ---- WebEngine must be imported before QApplication is created (best practice) ----
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

WEBENGINE_AVAILABLE = False
try:
    from PySide6 import QtWebEngineWidgets  # noqa: F401
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebChannel import QWebChannel
    WEBENGINE_AVAILABLE = True
except Exception:
    QWebEngineView = None  # type: ignore
    QWebChannel = None  # type: ignore

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QMessageBox,
    QScrollArea,
    QFrame,
    QPushButton,
    QGraphicsOpacityEffect,
)


# ---- Optional Camera Support (QtMultimedia) ----
CAMERA_AVAILABLE = False
try:
    from PySide6.QtMultimedia import QMediaCaptureSession, QCamera, QImageCapture, QMediaRecorder
    from PySide6.QtMultimediaWidgets import QVideoWidget
    CAMERA_AVAILABLE = True
except Exception:
    QMediaCaptureSession = None  # type: ignore
    QCamera = None  # type: ignore
    QImageCapture = None  # type: ignore
    QMediaRecorder = None  # type: ignore
    QVideoWidget = None  # type: ignore


HERE = os.path.dirname(os.path.abspath(__file__))
NC_CONSOLE = os.path.join(HERE, "nc_console.py")


# -----------------------------
# TWIN parse
# -----------------------------

def _try_parse_twin(line: str) -> dict | None:
    if not line.startswith("__TWIN__"):
        return None
    payload = line[len("__TWIN__"):].strip()

    # 1) direct JSON
    if payload.startswith("{") and payload.endswith("}"):
        try:
            obj = json.loads(payload)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    # 2) base64(JSON)
    try:
        raw = base64.b64decode(payload.encode("ascii"), validate=False)
        obj = json.loads(raw.decode("utf-8", errors="replace"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# -----------------------------
# Plot canvas (no external libs)
# -----------------------------

class PlotCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.series: dict[str, list[tuple[int, float]]] = {}
        self.max_points = 3000
        self.setMinimumHeight(260)

    def clear(self):
        self.series.clear()
        self.update()

    def add_point(self, series: str, step: int, value: float):
        series = str(series)
        pts = self.series.get(series)
        if pts is None:
            pts = []
            self.series[series] = pts
        pts.append((int(step), float(value)))
        if len(pts) > self.max_points:
            del pts[: len(pts) - self.max_points]
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        h = self.height()

        # background
        p.fillRect(0, 0, w, h, QColor(18, 18, 22))

        # margins
        L, R, T, B = 55, 12, 12, 28
        rect = QRectF(L, T, max(1, w - L - R), max(1, h - T - B))

        # axes box
        p.setPen(QPen(QColor(120, 120, 140), 1))
        p.drawRect(rect)

        if not self.series:
            p.setPen(QPen(QColor(180, 180, 200), 1))
            p.drawText(rect, Qt.AlignCenter, "No plot data yet…")
            return

        # bounds
        min_x = None
        max_x = None
        min_y = None
        max_y = None
        for pts in self.series.values():
            for x, y in pts:
                min_x = x if min_x is None else min(min_x, x)
                max_x = x if max_x is None else max(max_x, x)
                min_y = y if min_y is None else min(min_y, y)
                max_y = y if max_y is None else max(max_y, y)

        if min_x is None or max_x is None or min_y is None or max_y is None:
            return

        if min_x == max_x:
            max_x = min_x + 1
        if min_y == max_y:
            max_y = min_y + 1.0

        # add small y padding
        ypad = (max_y - min_y) * 0.05
        min_y -= ypad
        max_y += ypad

        def tx(x: int) -> float:
            return rect.left() + (x - min_x) / (max_x - min_x) * rect.width()

        def ty(y: float) -> float:
            return rect.bottom() - (y - min_y) / (max_y - min_y) * rect.height()

        # labels
        p.setPen(QPen(QColor(170, 170, 190), 1))
        p.drawText(8, 20, f"y: [{min_y:.3g} .. {max_y:.3g}]")
        p.drawText(8, h - 8, f"x: [{min_x} .. {max_x}]")

        # draw series
        for name, pts in self.series.items():
            if len(pts) < 2:
                continue

            # deterministic pseudo color from hash
            hv = abs(hash(name)) % 1000
            r = 80 + (hv % 150)
            g = 120 + ((hv // 3) % 120)
            b = 160 + ((hv // 7) % 95)
            color = QColor(r % 255, g % 255, b % 255)

            p.setPen(QPen(color, 2))
            x0, y0 = pts[0]
            for x1, y1 in pts[1:]:
                p.drawLine(int(tx(x0)), int(ty(y0)), int(tx(x1)), int(ty(y1)))
                x0, y0 = x1, y1


# -----------------------------
# HTML helpers (inject CSS/JS + WebChannel bridge)
# -----------------------------

_BRIDGE_INJECT = r"""
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
(function(){
  try{
    function init(){
      try{
        if (typeof QWebChannel === "undefined" || !window.qt || !qt.webChannelTransport) return;
        new QWebChannel(qt.webChannelTransport, function(channel){
          window.ncHost = channel.objects.ncHost || null;
          window.ncSend = function(msg){
            try{
              if (window.ncHost && window.ncHost.send) window.ncHost.send(String(msg));
            }catch(e){}
          };
          try{
            if (window.ncHost && window.ncHost.ready) window.ncHost.ready();
          }catch(e){}
        });
      }catch(e){}
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
  }catch(e){}
})();
</script>
"""

def _insert_before_closing_head(doc: str, injection: str) -> str:
    lo = doc.lower()
    idx = lo.rfind("</head>")
    if idx >= 0:
        return doc[:idx] + injection + doc[idx:]
    return doc

def _wrap_as_document(body_html: str, extra_head: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        + extra_head
        + "</head><body>"
        + body_html
        + "</body></html>"
    )

def _compose_html(html: str, extra_css: str = "", extra_js: str = "", enable_bridge: bool = True) -> str:
    """
    Takes any HTML snippet or full document and injects:
    - <style>extra_css</style>
    - <script>bridge + extra_js</script>
    """
    html = html or ""
    extra_css = extra_css or ""
    extra_js = extra_js or ""

    head_bits = ""
    if extra_css.strip():
        head_bits += f"<style>\n{extra_css}\n</style>\n"
    if enable_bridge and WEBENGINE_AVAILABLE:
        head_bits += _BRIDGE_INJECT + "\n"
    if extra_js.strip():
        head_bits += f"<script>\n{extra_js}\n</script>\n"

    lo = html.lower()

    # If it's a full document, inject into <head> if possible.
    if "<html" in lo:
        # If there is a head section, inject before </head>, else create head after <html...>
        if "<head" in lo:
            out = _insert_before_closing_head(html, head_bits)
            if out != html:
                return out
            # head exists but no </head> found -> just append head bits at start
            return head_bits + html
        # no head => best-effort: insert head bits right after <html...>
        pos = lo.find("<html")
        gt = lo.find(">", pos) if pos >= 0 else -1
        if gt >= 0:
            return html[:gt + 1] + "<head>" + head_bits + "</head>" + html[gt + 1:]
        return _wrap_as_document(html, head_bits)

    # Not a full document => treat as body snippet
    return _wrap_as_document(html, head_bits)


# -----------------------------
# JS bridge object (JS -> Python log)
# -----------------------------

class WebBridge(QObject):
    message = Signal(str)

    @Slot(str)
    def send(self, msg: str):
        self.message.emit(str(msg))

    @Slot()
    def ready(self):
        self.message.emit("[bridge] ready")


# -----------------------------
# Twin window UI
# -----------------------------

class TwinWindow(QMainWindow):
    def __init__(self, wid: str, title: str, w: int, h: int):
        super().__init__()
        self.wid = wid
        self.setWindowTitle(title)
        self.resize(w, h)

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(10, 10, 10, 10)

        self.header = QLabel(f"NC Window: {title}")
        self.header.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.header.setStyleSheet("font-weight: 800; font-size: 16px;")

        self.tabs = QTabWidget()

        # --- Log tab ---
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Waiting for output...")
        self.tabs.addTab(self.log, "Log")

        # --- Plots tab ---
        plot_root = QWidget()
        plot_lay = QVBoxLayout(plot_root)
        plot_lay.setContentsMargins(8, 8, 8, 8)

        self.plot_canvas = PlotCanvas()
        plot_lay.addWidget(self.plot_canvas, 1)
        self.tabs.addTab(plot_root, "Plots")

        # --- Tables tab ---
        tables_root = QWidget()
        tables_lay = QVBoxLayout(tables_root)
        tables_lay.setContentsMargins(8, 8, 8, 8)

        self.table_selector = QComboBox()
        self.table_widget = QTableWidget()
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["C0", "C1"])
        self.table_widget.horizontalHeader().setStretchLastSection(True)

        self.tables: dict[str, list[list[object]]] = {}
        self.table_selector.currentTextChanged.connect(self._render_selected_table)

        tables_lay.addWidget(self.table_selector)
        tables_lay.addWidget(self.table_widget, 1)
        self.tabs.addTab(tables_root, "Tables")

        # --- HTML tab ---
        # If WebEngine available => full HTML/CSS/JS/SVG + bridge
        # Else fallback => QTextEdit.setHtml (no JS)
        self._web_bridge = None
        self._web_channel = None

        if WEBENGINE_AVAILABLE:
            self.html = QWebEngineView()
            # Install WebChannel bridge so JS can call ncSend("...")
            try:
                self._web_bridge = WebBridge()
                self._web_bridge.message.connect(lambda m: self.append_log(f"[js] {m}"))
                self._web_channel = QWebChannel(self.html.page())
                self._web_channel.registerObject("ncHost", self._web_bridge)
                self.html.page().setWebChannel(self._web_channel)
            except Exception as e:
                self.append_log(f"[warn] WebChannel init failed: {e}")

            self.html.setHtml(
                _compose_html(
                    "<div style='background:#111;color:#ddd;font-family:Segoe UI;padding:14px;'>No HTML content yet…</div>",
                    enable_bridge=True,
                )
            )
        else:
            self.html = QTextEdit()
            self.html.setReadOnly(True)
            self.html.setPlaceholderText("QtWebEngine missing: HTML shown without JS. Install PySide6-QtWebEngine.")
        self.tabs.addTab(self.html, "HTML")

        # --- UI tab (NCUI2: no HTML/CSS) ---
        self.ui2_root = QWidget()
        self.ui2_lay = QVBoxLayout(self.ui2_root)
        self.ui2_lay.setContentsMargins(12, 12, 12, 12)
        self.ui2_lay.setSpacing(10)

        self.ui2_scroll = QScrollArea()
        self.ui2_scroll.setWidgetResizable(True)
        self.ui2_scroll.setFrameShape(QFrame.NoFrame)
        self.ui2_scroll.setWidget(self.ui2_root)
        self.tabs.addTab(self.ui2_scroll, "UI")


        # --- Camera tab ---
        cam_root = QWidget()
        cam_lay = QVBoxLayout(cam_root)
        cam_lay.setContentsMargins(8, 8, 8, 8)

        self._cam_session = None
        self._cam = None
        self._cam_image = None
        self._cam_recorder = None
        self._cam_video = None

        if CAMERA_AVAILABLE and QVideoWidget is not None:
            self._cam_video = QVideoWidget()
            cam_lay.addWidget(self._cam_video, 1)
            info = QLabel("Camera bereit. Verwende cam.open(...) in NC.")
            info.setStyleSheet("opacity:.8;")
            cam_lay.addWidget(info)
        else:
            info = QLabel("Camera nicht verfügbar: QtMultimedia fehlt. Install: pip install PySide6")
            info.setStyleSheet("opacity:.8;")
            cam_lay.addWidget(info, 1)

        self.tabs.addTab(cam_root, "Camera")

        lay.addWidget(self.header)
        lay.addWidget(self.tabs, 1)
        self.setCentralWidget(root)

    def append_log(self, text: str):
        self.log.append(text)

    def set_title(self, title: str):
        self.setWindowTitle(title)
        self.header.setText(f"NC Window: {title}")

    def set_table(self, name: str, rows: list[list[object]]):
        name = str(name)
        self.tables[name] = rows
        if self.table_selector.findText(name) < 0:
            self.table_selector.addItem(name)
        self.table_selector.setCurrentText(name)
        self.tabs.setCurrentIndex(2)

    def _render_selected_table(self, name: str):
        rows = self.tables.get(name) or []

        # max columns
        max_cols = 0
        for r in rows:
            if isinstance(r, list):
                max_cols = max(max_cols, len(r))
        if max_cols <= 0:
            max_cols = 1

        self.table_widget.clear()
        self.table_widget.setRowCount(len(rows))
        self.table_widget.setColumnCount(max_cols)

        # If first row is all strings, treat as header row (optional)
        headers = []
        if rows and isinstance(rows[0], list) and rows[0] and all(isinstance(x, str) for x in rows[0]):
            if len(rows[0]) == max_cols:
                headers = [str(x) for x in rows[0]]

        if headers:
            self.table_widget.setHorizontalHeaderLabels(headers)
        else:
            self.table_widget.setHorizontalHeaderLabels([f"C{i}" for i in range(max_cols)])

        for i, r in enumerate(rows):
            if not isinstance(r, list):
                r = [r]
            for j in range(max_cols):
                val = r[j] if j < len(r) else ""
                item = QTableWidgetItem(str(val))
                self.table_widget.setItem(i, j, item)

        self.table_widget.resizeColumnsToContents()
        self.table_widget.horizontalHeader().setStretchLastSection(True)

    def add_plot_point(self, series: str, step: int, value: float):
        self.plot_canvas.add_point(series, step, value)
        self.tabs.setCurrentIndex(1)

    def set_html(self, html: str, css: str = "", js: str = ""):
        # WebEngine: full JS/CSS/SVG
        if WEBENGINE_AVAILABLE and hasattr(self.html, "setHtml"):
            doc = _compose_html(html, extra_css=css, extra_js=js, enable_bridge=True)
            self.html.setHtml(doc)
            self.tabs.setCurrentIndex(3)
            return

        # fallback: QTextEdit (no JS)
        if isinstance(self.html, QTextEdit):
            # Keep CSS applied in fallback (works), JS ignored (no engine)
            doc = _compose_html(html, extra_css=css, extra_js="", enable_bridge=False)
            self.html.setHtml(doc)
            self.tabs.setCurrentIndex(3)
            if (js or "").strip():
                self.append_log("[warn] QtWebEngine missing => JS cannot run in HTML tab.")
            return

        self.append_log("[warn] HTML renderer not available")

    def eval_js(self, code: str):
        if not WEBENGINE_AVAILABLE or not hasattr(self.html, "page"):
            self.append_log("[warn] JS eval not available (QtWebEngine missing).")
            return
        try:
            # runJavaScript is async; log the returned value if any
            self.html.page().runJavaScript(
                code,
                lambda result: self.append_log(f"[js.result] {result!r}")
            )
        except Exception as e:
            self.append_log(f"[warn] JS eval failed: {e}")


    # ---------- NCUI2 (no HTML/CSS) ----------

    def ui2_clear(self):
        # remove widgets from layout
        while self.ui2_lay.count():
            item = self.ui2_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def ui2_set_scene(self, scene: dict):
        """Render a simple scene graph produced by NC's UI DSL without using HTML/CSS."""
        try:
            self.ui2_clear()
            nodes = scene.get("nodes", []) if isinstance(scene, dict) else []
            styles = scene.get("styles", {}) if isinstance(scene, dict) else {}
            anims = scene.get("anims", {}) if isinstance(scene, dict) else {}

            for n in nodes if isinstance(nodes, list) else []:
                if not isinstance(n, dict):
                    continue
                tag = str(n.get("tag", "text")).lower()
                txt = n.get("text")
                if tag in ("button", "btn"):
                    w = QPushButton(str(txt or n.get("label") or "Button"))
                else:
                    w = QLabel(str(txt or ""))
                    w.setWordWrap(True)

                # Apply style (use + inline)
                props = {}
                use = n.get("use")
                if use and isinstance(styles, dict) and use in styles:
                    props.update(styles.get(use) or {})
                inline = n.get("props")
                if isinstance(inline, dict):
                    props.update(inline)

                # font
                try:
                    f = w.font()
                    fs = props.get("font_size")
                    if fs is not None:
                        f.setPointSizeF(float(fs))
                    fw = props.get("font_weight")
                    if fw is not None:
                        try:
                            f.setWeight(int(fw))
                        except Exception:
                            pass
                    w.setFont(f)
                except Exception:
                    pass

                # color / opacity
                try:
                    col = props.get("color")
                    if isinstance(col, (list, tuple)) and len(col) >= 3:
                        qcol = QColor(int(col[0]), int(col[1]), int(col[2]))
                        pal = w.palette()
                        pal.setColor(w.foregroundRole(), qcol)
                        w.setPalette(pal)
                    op = props.get("opacity")
                    if op is not None:
                        eff = QGraphicsOpacityEffect()
                        eff.setOpacity(max(0.0, min(1.0, float(op))))
                        w.setGraphicsEffect(eff)
                except Exception:
                    pass

                self.ui2_lay.addWidget(w)

                # very small animation support: fadeIn
                anim_name = n.get("anim")
                if anim_name and isinstance(anims, dict) and anim_name in anims:
                    # for now: if keyframes mention opacity 0->1, animate opacity
                    kf = anims.get(anim_name) or {}
                    try:
                        eff = w.graphicsEffect()
                        if not isinstance(eff, QGraphicsOpacityEffect):
                            eff = QGraphicsOpacityEffect()
                            eff.setOpacity(0.0)
                            w.setGraphicsEffect(eff)
                        # We intentionally keep it simple (no heavy UI rebuild)
                        from PySide6.QtCore import QPropertyAnimation
                        anim = QPropertyAnimation(eff, b"opacity", w)
                        anim.setStartValue(float(kf.get("opacity_from", 0.0)))
                        anim.setEndValue(float(kf.get("opacity_to", 1.0)))
                        anim.setDuration(int(kf.get("duration_ms", 600)))
                        anim.start()
                    except Exception:
                        pass

            self.tabs.setCurrentIndex(self.tabs.indexOf(self.ui2_scroll))
        except Exception as e:
            self.append_log(f"[ui2] render failed: {e}")

    # ---------- Camera support (optional) ----------

    def camera_open(self, facing: str = "back", w: int = 1280, h: int = 720, fps: int = 30):
        if not CAMERA_AVAILABLE:
            self.append_log("[camera] QtMultimedia not available.")
            return False
        try:
            # Lazy init
            if self._cam_session is None:
                self._cam_session = QMediaCaptureSession()
            if self._cam is None:
                # Choose default camera (facing is best-effort; Qt chooses default)
                self._cam = QCamera()
                self._cam_session.setCamera(self._cam)
            if self._cam_video is not None:
                self._cam_session.setVideoOutput(self._cam_video)
            if self._cam_image is None:
                self._cam_image = QImageCapture()
                self._cam_session.setImageCapture(self._cam_image)
            if self._cam_recorder is None:
                self._cam_recorder = QMediaRecorder()
                self._cam_session.setRecorder(self._cam_recorder)

            # Start camera
            self._cam.start()
            self.tabs.setCurrentIndex(self.tabs.indexOf(self._cam_video.parentWidget() if self._cam_video else self.tabs.widget(4)))
            self.append_log(f"[camera] open facing={facing} {w}x{h}@{fps}")
            return True
        except Exception as e:
            self.append_log(f"[camera] open failed: {e}")
            return False

    def camera_close(self):
        try:
            if self._cam is not None:
                self._cam.stop()
            self.append_log("[camera] closed")
        except Exception as e:
            self.append_log(f"[camera] close failed: {e}")

    def camera_snap(self, path: str):
        if not CAMERA_AVAILABLE or self._cam_image is None:
            self.append_log("[camera] snap not available")
            return
        try:
            # QImageCapture stores to file path
            self._cam_image.captureToFile(str(path))
            self.append_log(f"[camera] snap -> {path}")
        except Exception as e:
            self.append_log(f"[camera] snap failed: {e}")

    def camera_record_start(self, path: str, w: int = 1280, h: int = 720, fps: int = 30):
        if not CAMERA_AVAILABLE or self._cam_recorder is None:
            self.append_log("[camera] recorder not available")
            return
        try:
            # best-effort: set output location
            from PySide6.QtCore import QUrl
            self._cam_recorder.setOutputLocation(QUrl.fromLocalFile(str(path)))
            self._cam_recorder.record()
            self.append_log(f"[camera] record_start -> {path}")
        except Exception as e:
            self.append_log(f"[camera] record_start failed: {e}")

    def camera_record_stop(self):
        if not CAMERA_AVAILABLE or self._cam_recorder is None:
            self.append_log("[camera] recorder not available")
            return
        try:
            self._cam_recorder.stop()
            self.append_log("[camera] record_stop")
        except Exception as e:
            self.append_log(f"[camera] record_stop failed: {e}")

    def camera_set(self, key: str, value):
        # Placeholder: different backends expose different controls
        self.append_log(f"[camera] set {key}={value} (not implemented)")




# -----------------------------
# Host process + command router
# -----------------------------

class HostApp:
    def __init__(self, argv: list[str]):
        self.app = QApplication.instance() or QApplication(argv)

        self.windows: dict[str, TwinWindow] = {}
        self.default_window_id = "nc_sim"

        self.proc = QProcess()
        py = sys.executable
        self.proc.setProgram(py)
        self.proc.setArguments([NC_CONSOLE] + argv[1:])
        self.proc.setWorkingDirectory(HERE)

        self.proc.readyReadStandardOutput.connect(self._on_stdout)
        self.proc.readyReadStandardError.connect(self._on_stderr)
        self.proc.finished.connect(self._on_finished)

        self._buf_out = ""
        self._buf_err = ""

    def run(self) -> int:
        self.proc.start()
        if not self.proc.waitForStarted(5000):
            print("NCW GUI: Failed to start nc_console.py")
            return 2

        QTimer.singleShot(250, self._ensure_console_window)
        return self.app.exec()

    def _ensure_console_window(self):
        """Ensure the default console/log window exists.

        Output can arrive before the startup timer fires *or* after another window
        has already been created via a TWIN command. In both cases we must avoid
        crashing with KeyError when appending plain stdout/stderr lines.
        """

        # If the default id already exists, we're done.
        if self.default_window_id in self.windows:
            return

        # If some other window exists already, use it as the default sink.
        if self.windows and self.default_window_id not in self.windows:
            self.default_window_id = next(iter(self.windows.keys()))
            return

        # Otherwise create the default window.
        w = TwinWindow(self.default_window_id, "NC Output", 1000, 700)
        w.show()
        self.windows[self.default_window_id] = w
        if not WEBENGINE_AVAILABLE:
            w.append_log("[info] QtWebEngine not available => HTML shows without JS. Install PySide6-QtWebEngine.")
        else:
            w.append_log("[info] HTML tab supports JS. In HTML you can call: ncSend('hi')")

    def _default_log_window(self):
        """Return a safe window to append logs to (never raises KeyError)."""
        self._ensure_console_window()
        win = self.windows.get(self.default_window_id)
        if win is None and self.windows:
            win = next(iter(self.windows.values()))
            # Keep default_window_id in sync for subsequent log appends.
            for k, v in self.windows.items():
                if v is win:
                    self.default_window_id = k
                    break
        return win

    def _get_or_create_window(self, wid: str, title: str, w: int, h: int) -> TwinWindow:
        wid = str(wid)
        title = str(title)
        win = self.windows.get(wid)
        if win is None:
            win = TwinWindow(wid, title, w, h)
            self.windows[wid] = win
            win.show()
            if not WEBENGINE_AVAILABLE:
                win.append_log("[info] QtWebEngine not available => HTML shows without JS. Install PySide6-QtWebEngine.")
            else:
                win.append_log("[info] HTML tab supports JS. In HTML you can call: ncSend('hi')")
        else:
            win.set_title(title)
            win.resize(w, h)
            win.show()
        win.raise_()
        win.activateWindow()
        return win

    # ---------- messagebox (t_windows style) ----------

    def _msgbox(self, kind: str, title: str, message: str, default: bool = False):
        mb = QMessageBox()
        mb.setWindowTitle(title or "Message")
        mb.setText(message or "")

        k = (kind or "").lower()
        if k == "info":
            mb.setIcon(QMessageBox.Information)
            mb.setStandardButtons(QMessageBox.Ok)
        elif k == "warning":
            mb.setIcon(QMessageBox.Warning)
            mb.setStandardButtons(QMessageBox.Ok)
        elif k == "error":
            mb.setIcon(QMessageBox.Critical)
            mb.setStandardButtons(QMessageBox.Ok)
        elif k == "askyesno":
            mb.setIcon(QMessageBox.Question)
            mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            mb.setDefaultButton(QMessageBox.Yes if default else QMessageBox.No)
        else:
            mb.setIcon(QMessageBox.Information)
            mb.setStandardButtons(QMessageBox.Ok)

        return mb.exec()

    # ---------- command handler ----------

    def _handle_twin(self, cmd: dict):
        # Normalize: support both "cmd" (NC) and "action" (t_windows)
        c = cmd.get("cmd") or cmd.get("action")

        # --- window open/create ---
        if c in ("window.open", "create", "window"):
            wid = str(cmd.get("id", self.default_window_id))
            title = str(cmd.get("title", "NC"))
            w = int(cmd.get("w", 1000))
            h = int(cmd.get("h", 700))
            win = self._get_or_create_window(wid, title, w, h)

            # t_windows can send content_html (+ optional css/js)
            content_html = cmd.get("content_html")
            content_css = cmd.get("content_css", "")
            content_js = cmd.get("content_js", "")
            if isinstance(content_html, str) and content_html.strip():
                win.set_html(content_html, css=str(content_css or ""), js=str(content_js or ""))
            return

        # --- window close ---
        if c in ("window.close", "close"):
            wid = str(cmd.get("id", self.default_window_id))
            win = self.windows.pop(wid, None)
            if win:
                win.close()
            return

        # --- t_windows init ---
        if c == "init":
            self._ensure_console_window()
            self.windows[self.default_window_id].append_log(f"[init] {cmd}")

            # If it contains windows, open them
            wins = cmd.get("windows")
            if isinstance(wins, list):
                for wobj in wins:
                    if isinstance(wobj, dict):
                        w_id = str(wobj.get("id", self.default_window_id))
                        title = str(wobj.get("title", "TWIN"))
                        ww = int(wobj.get("w", 1000))
                        hh = int(wobj.get("h", 700))
                        win = self._get_or_create_window(w_id, title, ww, hh)
                        html = wobj.get("content_html")
                        css = wobj.get("content_css", "")
                        js = wobj.get("content_js", "")
                        if isinstance(html, str) and html.strip():
                            win.set_html(html, css=str(css or ""), js=str(js or ""))
            return

        # --- message boxes (t_windows) ---
        if c == "msgbox":
            kind = str(cmd.get("kind", "info"))
            title = str(cmd.get("title", "Message"))
            message = str(cmd.get("message", ""))
            default = bool(cmd.get("default", False))
            self._msgbox(kind, title, message, default=default)
            return


        # --- UI2 scene set (no HTML/CSS) ---
        if c in ("ui.scene", "ui2.scene", "scene.set"):
            wid = str(cmd.get("id", self.default_window_id))
            title = str(cmd.get("title", self.windows.get(wid).windowTitle() if wid in self.windows else "NC"))
            win = self._get_or_create_window(wid, title, 1000, 700)
            scene = cmd.get("scene", cmd.get("ui", {}))
            if isinstance(scene, dict):
                win.ui2_set_scene(scene)
            else:
                win.append_log(f"[ui.scene] bad scene type: {type(scene)}")
            return

        # --- HTML set (explicit) ---
        if c in ("html.set", "window.html", "html"):
            wid = str(cmd.get("id", self.default_window_id))
            title = str(cmd.get("title", self.windows.get(wid).windowTitle() if wid in self.windows else "NC"))
            win = self._get_or_create_window(wid, title, 1000, 700)

            html = str(cmd.get("html", cmd.get("content_html", "")) or "")
            css = str(cmd.get("css", cmd.get("content_css", "")) or "")
            js = str(cmd.get("js", cmd.get("content_js", "")) or "")
            win.set_html(html, css=css, js=js)
            return

        # --- JS eval (run code on current HTML tab) ---
        if c in ("html.eval", "js.eval", "window.eval_js"):
            wid = str(cmd.get("id", self.default_window_id))
            win = self.windows.get(wid) or self.windows.get(self.default_window_id)
            if win is None:
                self._ensure_console_window()
                win = self.windows[self.default_window_id]
            code = str(cmd.get("code", cmd.get("js", "")) or "")
            if not code.strip():
                win.append_log("[warn] html.eval missing 'code'")
                return
            win.eval_js(code)
            return

        # --- table.set (NC UI bridge) ---
        if c == "table.set":
            wid = str(cmd.get("id", self.default_window_id))
            name = str(cmd.get("name", "table"))
            rows = cmd.get("rows", [])
            win = self._get_or_create_window(
                wid,
                self.windows.get(wid).windowTitle() if wid in self.windows else "NC",
                1000,
                700,
            )
            if isinstance(rows, list):
                win.set_table(name, rows)
            else:
                win.append_log(f"[table.set] bad rows type: {type(rows)}")
            return

        # --- plot.add (NC UI bridge) ---
        if c == "plot.add":
            wid = str(cmd.get("id", self.default_window_id))
            series = str(cmd.get("series", "series"))
            step = int(cmd.get("step", 0))
            value = float(cmd.get("value", 0.0))
            win = self._get_or_create_window(
                wid,
                self.windows.get(wid).windowTitle() if wid in self.windows else "NC",
                1000,
                700,
            )
            win.add_plot_point(series, step, value)
            return

        
        # --- camera.* (NC cam bridge) ---
        if c in ("camera.open", "camera.close", "camera.snap", "camera.record_start", "camera.record_stop", "camera.set"):
            wid = str(cmd.get("id", self.default_window_id))
            title = self.windows.get(wid).windowTitle() if wid in self.windows else "NC Camera"
            win = self._get_or_create_window(wid, title, 1000, 700)

            if c == "camera.open":
                facing = str(cmd.get("facing", "back"))
                ww = int(cmd.get("w", 1280))
                hh = int(cmd.get("h", 720))
                fps = int(cmd.get("fps", 30))
                win.camera_open(facing=facing, w=ww, h=hh, fps=fps)
                return

            if c == "camera.close":
                win.camera_close()
                return

            if c == "camera.snap":
                path = str(cmd.get("path", "snap.jpg"))
                win.camera_snap(path)
                return

            if c == "camera.record_start":
                path = str(cmd.get("path", "video.mp4"))
                ww = int(cmd.get("w", 1280))
                hh = int(cmd.get("h", 720))
                fps = int(cmd.get("fps", 30))
                win.camera_record_start(path, w=ww, h=hh, fps=fps)
                return

            if c == "camera.record_stop":
                win.camera_record_stop()
                return

            if c == "camera.set":
                key = str(cmd.get("key", ""))
                val = cmd.get("value")
                win.camera_set(key, val)
                return

# Unknown: log it
        self._ensure_console_window()
        self.windows[self.default_window_id].append_log(f"[TWIN] {cmd}")

    # ---------- IO line buffering ----------

    def _consume_lines(self, chunk: str, is_err: bool):
        buf = self._buf_err if is_err else self._buf_out
        buf += chunk

        lines = buf.splitlines(keepends=False)

        # keep last partial line if no newline
        if buf and not buf.endswith("\n") and lines:
            buf = lines.pop()
        else:
            buf = ""

        if is_err:
            self._buf_err = buf
        else:
            self._buf_out = buf

        for line in lines:
            stripped = line.strip()
            tw = _try_parse_twin(stripped)
            if tw is not None:
                self._handle_twin(tw)
            else:
                self._ensure_console_window()
                prefix = "[stderr] " if is_err else ""
                win = self._default_log_window()
                if win is not None:
                    win.append_log(prefix + line)
                else:
                    print(prefix + line)

    def _on_stdout(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._consume_lines(data, is_err=False)

    def _on_stderr(self):
        data = bytes(self.proc.readAllStandardError()).decode("utf-8", errors="replace")
        self._consume_lines(data, is_err=True)

    def _on_finished(self, code: int, status):
        self._ensure_console_window()
        # Guard: default_window_id might not exist if window creation failed/changed.
        win = self.windows.get(self.default_window_id)
        if win is None and self.windows:
            win = next(iter(self.windows.values()))
        if win is not None:
            win.append_log(f"\n[NCW GUI] process finished (code={code})")
        else:
            print(f"[NCW GUI] process finished (code={code})")
        # keep windows open


def main() -> int:
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        os.system(f'"{sys.executable}" "{NC_CONSOLE}" --help')
        return 0

    host = HostApp(sys.argv)
    return host.run()


if __name__ == "__main__":
    raise SystemExit(main())
