import os
import sys
import re
import io
import json
import time
import queue
import shutil
import signal
import zipfile
import mimetypes
import tempfile
import threading
import urllib.parse
import subprocess
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import nc

MAX_BODY_BYTES = 512_000
MAX_CODE_BYTES = 200_000
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080
ALLOWED_IP = "192.168.2.105"
UPLOADS_DIRNAME = "uploads"
IPS_FILENAME = "ips.json"

PLAYGROUND_HTML = """<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>NC Browser Runner</title>
  <style>
    :root{color-scheme:dark}
    *{box-sizing:border-box}
    body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#0f1115;color:#eef2ff}
    .wrap{max-width:1320px;margin:0 auto;padding:18px}
    .card{background:#171a21;border:1px solid #2b3140;border-radius:16px;padding:16px;box-shadow:0 8px 28px rgba(0,0,0,.25)}
    h1{margin:0 0 8px 0;font-size:24px}
    .muted{color:#9aa4b8;font-size:14px}
    .grid{display:grid;grid-template-columns:1.2fr .8fr;gap:14px;margin-top:14px}
    @media (max-width:980px){.grid{grid-template-columns:1fr}}
    textarea,input,select{width:100%;border:1px solid #31384a;border-radius:12px;background:#0f131b;color:#eef2ff;padding:12px;font:14px/1.4 Consolas,Monaco,monospace}
    input,select{font-family:Arial,Helvetica,sans-serif}
    textarea{min-height:520px;resize:vertical}
    button{border:1px solid #4d6bff;background:#3555ff;color:white;padding:10px 14px;border-radius:12px;font-weight:700;cursor:pointer}
    button.ghost{background:#1a2030;border-color:#39445f}
    button.warn{background:#402615;border-color:#7c4b2d}
    button:hover{filter:brightness(1.08)}
    .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
    .stack{display:flex;flex-direction:column;gap:10px}
    pre{margin:0;white-space:pre-wrap;word-break:break-word;background:#0f131b;border:1px solid #31384a;border-radius:12px;padding:12px;min-height:260px;max-height:520px;overflow:auto}
    .err{color:#ffb4b4}
    .ok{color:#b7ffd0}
    .small{font-size:12px;color:#90a0bf}
    .badge{display:inline-block;padding:4px 8px;border-radius:999px;background:#1b2340;border:1px solid #33406c;font-size:12px;color:#b8c7ff}
    .hint{background:#101622;border:1px solid #22304a;border-radius:12px;padding:10px;font-size:13px;color:#b8c7ff}
    .examples{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    @media (max-width:980px){.examples{grid-template-columns:1fr}}
    .pill{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:999px;background:#101622;border:1px solid #2a3757;font-size:12px;color:#b8c7ff}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>NC Browser Runner <span class="badge">NC only</span></h1>
      <div class="muted">Führt NC-Code direkt aus. Für interaktive NC-Dateien gibt es zusätzlich die IP-Route unten.</div>
      <div class="row" style="margin-top:12px">
        <button id="runBtn" type="button">▶ Ausführen</button>
        <button id="saveBtn" class="ghost" type="button">💾 Im Browser speichern</button>
        <button id="loadBtn" class="ghost" type="button">📂 Laden</button>
        <button id="clearBtn" class="warn" type="button">🗑 Leeren</button>
      </div>
      <div class="row" style="margin-top:10px">
        <input id="pathInput" placeholder="Virtueller Pfad für Fehlermeldungen, z.B. browser_demo.nc" value="browser_demo.nc" />
        <select id="exampleSelect">
          <option value="">Beispiel laden …</option>
          <option value="hello">Hallo Welt</option>
          <option value="math">Rechnen</option>
          <option value="ifdemo">If/Else</option>
          <option value="loopdemo">Repeat/Loop</option>
        </select>
      </div>
    </div>

    <div class="grid">
      <div class="card stack">
        <div class="muted">Code</div>
        <textarea id="codeInput">print "Hallo aus NC im Browser!"
let x = 5
let y = 7
print "x + y =", x + y</textarea>
        <div class="hint">Tipp: <span class="pill">Strg + Enter</span> zum Ausführen.</div>
      </div>

      <div class="card stack">
        <div class="row" style="justify-content:space-between">
          <div class="muted">Ausgabe</div>
          <div id="status" class="small">Bereit</div>
        </div>
        <pre id="output"></pre>
        <div class="small">Für interaktive NC-Dateien wie <code>input()</code> nutze <code>/ip/&lt;ip&gt;/&lt;datei.nc&gt;</code>.</div>
        <div class="examples">
          <div class="hint"><strong>Route:</strong><br><code>GET /__nc_playground</code></div>
          <div class="hint"><strong>API:</strong><br><code>POST /__nc_exec__</code></div>
        </div>
      </div>
    </div>
  </div>

<script>
const STORAGE_KEY = 'nc_browser_runner_code_v3';
const PATH_KEY = 'nc_browser_runner_path_v3';
const out = document.getElementById('output');
const statusEl = document.getElementById('status');
const codeEl = document.getElementById('codeInput');
const pathEl = document.getElementById('pathInput');
const exampleEl = document.getElementById('exampleSelect');

const EXAMPLES = {
  hello: 'print "Hallo aus NC!"\nprint "Das läuft im Browser als NC."',
  math: 'let a = 8\nlet b = 5\nprint "a + b =", a + b\nprint "a * b =", a * b\nprint "a / b =", a / b',
  ifdemo: 'let alter = 12\nif alter >= 12:\n  print "Du bist 12 oder älter."\nelse:\n  print "Du bist jünger als 12."',
  loopdemo: 'let n = 1\nrepeat 5:\n  print "Zeile", n\n  set n = n + 1'
};

function setStatus(text, cls=''){
  statusEl.className = 'small ' + cls;
  statusEl.textContent = text;
}

function saveLocal(){
  try{
    localStorage.setItem(STORAGE_KEY, codeEl.value || '');
    localStorage.setItem(PATH_KEY, pathEl.value || 'browser_demo.nc');
    setStatus('Im Browser gespeichert', 'ok');
  }catch(e){
    setStatus('Speichern fehlgeschlagen', 'err');
  }
}

function loadLocal(){
  try{
    const code = localStorage.getItem(STORAGE_KEY);
    const path = localStorage.getItem(PATH_KEY);
    if (code !== null) codeEl.value = code;
    if (path !== null) pathEl.value = path;
    setStatus(code !== null ? 'Geladen' : 'Nichts gespeichert');
  }catch(e){
    setStatus('Laden fehlgeschlagen', 'err');
  }
}

async function runCode(){
  setStatus('Läuft ...');
  out.textContent = '';
  try{
    const res = await fetch('/__nc_exec__', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({code: codeEl.value, path: pathEl.value || 'browser_demo.nc'})
    });
    const data = await res.json();
    if (!res.ok || !data.ok){
      out.textContent = data.error || ('HTTP ' + res.status);
      setStatus('Fehler', 'err');
      return;
    }
    out.textContent = data.output || '';
    setStatus('Fertig', 'ok');
    saveLocal();
  }catch(e){
    out.textContent = String(e && e.message ? e.message : e);
    setStatus('Fehler', 'err');
  }
}

document.getElementById('runBtn').addEventListener('click', runCode);
document.getElementById('saveBtn').addEventListener('click', saveLocal);
document.getElementById('loadBtn').addEventListener('click', loadLocal);
document.getElementById('clearBtn').addEventListener('click', () => {
  codeEl.value = '';
  out.textContent = '';
  setStatus('Editor geleert');
});
exampleEl.addEventListener('change', () => {
  if (!exampleEl.value || !EXAMPLES[exampleEl.value]) return;
  codeEl.value = EXAMPLES[exampleEl.value];
  setStatus('Beispiel geladen');
  exampleEl.value = '';
});
codeEl.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runCode();
});
loadLocal();
</script>
</body>
</html>
"""

INTERACTIVE_HTML = """<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>NC Script Output</title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; background: #f6f6f6; color: #222; margin: 20px; }
    .card { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    #output { white-space: pre-wrap; font-family: Consolas, Monaco, monospace; font-size: 13px; max-height: 420px; overflow-y: auto; padding: 10px; border-radius: 8px; border: 1px solid #ddd; background: #ffffff; }
    #textInput { width: 100%; max-width: 520px; padding: 10px; border-radius: 8px; border: 1px solid #ccc; margin-top: 10px; box-sizing: border-box; }
    #history { margin-top: 12px; font-family: Consolas, Monaco, monospace; font-size: 13px; }
    h2 { margin: 0 0 10px 0; }
    .meta { color: #666; font-size: 13px; margin-bottom: 8px; }
    .small { font-size: 12px; color:#777; }
  </style>
</head>
<body>
  <div class="card">
    <h2>📜 NC Script: __DATEINAME__</h2>
    <div class="meta">Verbunden als: <strong>__IP__</strong> — Server: <strong>__ALLOWED_IP__:__PORT__</strong></div>
    <div id="output"></div>
    <form id="inputForm">
      <input id="textInput" name="text" placeholder="Eingabe an das NC-Skript (ENTER zum Senden) ..." autocomplete="off" />
    </form>
    <div id="history" class="small"></div>
  </div>

  <script>
    const form = document.getElementById('inputForm');
    const input = document.getElementById('textInput');
    const output = document.getElementById('output');
    const historyDiv = document.getElementById('history');

    async function updateOutput() {
      try {
        const resp = await fetch('/get_output');
        const data = await resp.text();
        output.innerText = data;
        output.scrollTop = output.scrollHeight;

        const respHist = await fetch('/get_history');
        const histData = await respHist.json();
        historyDiv.innerHTML = histData.map(h => '→ ' + h).join('<br>');
      } catch (_e) {
      }
    }

    setInterval(updateOutput, 500);
    updateOutput();

    form.addEventListener('submit', async function(e) {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      await fetch('/input', {
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},
        body:'text=' + encodeURIComponent(text)
      });
    });
  </script>
</body>
</html>
"""


def _safe_join(root: str, rel: str) -> str:
    rel = rel.lstrip("/").replace("\\", "/")
    rel = os.path.normpath(rel)
    full = os.path.abspath(os.path.join(root, rel))
    root_abs = os.path.abspath(root)
    if not full.startswith(root_abs + os.sep) and full != root_abs:
        raise ValueError("blocked path traversal")
    return full


def _blocked_nc_text(code: str) -> str | None:
    checks = [
        (r"(^|\n)\s*import\s+py\b", "NC Browser Runner blockiert 'import py'."),
        (r"\bpy\s*\.", "NC Browser Runner blockiert die Python-Bridge 'py.'."),
        (r"(^|\n)\s*import\s+package\b", "NC Browser Runner blockiert 'import package'."),
        (r"(^|\n)\s*import\s+pkg\b", "NC Browser Runner blockiert 'import pkg'."),
    ]
    for pattern, message in checks:
        if re.search(pattern, code, flags=re.IGNORECASE):
            return message
    return None


def _build_search_paths(project_root: str) -> list[str]:
    return [
        project_root,
        os.path.join(project_root, "libs"),
        os.path.join(project_root, "api"),
        os.path.join(project_root, "api", "libs"),
        os.path.join(project_root, "www"),
        os.path.join(project_root, "www", "libs"),
    ]


def _run_nc_text_capture(nc_text: str, project_root: str, source_name: str = "<text>") -> tuple[str, dict]:
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        nc.run_text(
            nc_text,
            base=project_root,
            extra_paths=_build_search_paths(project_root),
            policy=nc.NCPolicy(
                allow_http=False,
                allow_private_hosts=True,
                data_dir=os.path.join(project_root, "_data"),
            ),
            enable_ui=False,
            source_name=source_name,
        )
    return buf.getvalue(), {"source": source_name}


def _run_nc_file(path: str, request_obj: dict, project_root: str) -> tuple[int, dict, bytes]:
    injected = f'let request = {json.dumps(request_obj, ensure_ascii=False)}\n'
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()
    text = injected + "\n" + code

    output, _meta = _run_nc_text_capture(text, project_root=project_root, source_name=path)
    out = output.splitlines()

    status = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}
    body_lines = out

    if out and out[0].startswith("__HTTP__"):
        meta_raw = out[0][len("__HTTP__"):].strip()
        try:
            meta = json.loads(meta_raw)
            status = int(meta.get("status", 200))
            h = meta.get("headers", {})
            if isinstance(h, dict):
                for k, v in h.items():
                    headers[str(k)] = str(v)
            body_lines = out[1:]
        except Exception:
            pass

    body = ("\n".join(body_lines)).encode("utf-8", errors="replace")
    return status, headers, body


class NCSession:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_process: subprocess.Popen[str] | None = None
        self.current_output: list[str] = []
        self.input_history: list[str] = []
        self.current_script: str = ""
        self.current_ip: str = ""
        self.reader_thread: threading.Thread | None = None

    def reset_buffers(self) -> None:
        with self.lock:
            self.current_output = []
            self.input_history = []

    def append_output(self, text: str) -> None:
        with self.lock:
            self.current_output.append(text)
            if len(self.current_output) > 4000:
                self.current_output = self.current_output[-4000:]

    def get_output_text(self) -> str:
        with self.lock:
            return "".join(self.current_output)

    def get_history(self) -> list[str]:
        with self.lock:
            return list(self.input_history)

    def add_history(self, text: str) -> None:
        with self.lock:
            self.input_history.append(text)
            if len(self.input_history) > 300:
                self.input_history = self.input_history[-300:]

    def stop_process(self) -> None:
        proc = self.current_process
        if not proc or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=1.5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _ips_path(root: str) -> str:
    return os.path.join(root, IPS_FILENAME)


def _uploads_dir(root: str) -> str:
    return os.path.join(root, UPLOADS_DIRNAME)


def _ensure_uploads(root: str) -> None:
    os.makedirs(_uploads_dir(root), exist_ok=True)


def _load_ips(root: str) -> dict:
    path = _ips_path(root)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _save_ips(root: str, ips: dict) -> None:
    path = _ips_path(root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ips, f, indent=4, ensure_ascii=False)


def _ensure_allowed_ip_registered(root: str) -> None:
    ips = _load_ips(root)
    if ALLOWED_IP not in ips:
        ips[ALLOWED_IP] = {"datei": ""}
        _save_ips(root, ips)


def _safe_nc_filename(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_\-. ]+\.nc", name or "", flags=re.IGNORECASE))


def _nc_console_path(root: str) -> str:
    candidates = [
        os.path.join(root, "nc_console.py"),
        os.path.join(os.path.dirname(__file__), "nc_console.py"),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    raise FileNotFoundError("nc_console.py nicht gefunden")


def _start_nc_script(session: NCSession, root: str, dateiname: str, ip: str) -> str | None:
    if not _safe_nc_filename(dateiname):
        return "Erlaubt sind nur .nc Dateien."

    uploads_dir = _uploads_dir(root)
    path = os.path.join(uploads_dir, dateiname)
    if not os.path.isfile(path):
        return f"Datei {dateiname} nicht gefunden!"

    session.stop_process()
    session.reset_buffers()
    session.current_script = dateiname
    session.current_ip = ip

    try:
        cmd = [sys.executable, "-u", _nc_console_path(root), path]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=root,
            env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1"),
        )
    except Exception as e:
        return f"NC Prozess konnte nicht gestartet werden: {e}"

    session.current_process = proc

    def reader() -> None:
        try:
            assert proc.stdout is not None
            while True:
                line = proc.stdout.readline()
                if line == "" and proc.poll() is not None:
                    break
                if line:
                    session.append_output(line)
        except Exception as e:
            session.append_output(f"\n[Reader-Error] {e}\n")

    t = threading.Thread(target=reader, daemon=True)
    session.reader_thread = t
    t.start()
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = "NCServer/1.5"

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_DELETE(self):
        self._handle()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_bytes(self, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8", extra_headers: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(str(k), str(v))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, text: str, content_type: str = "text/plain; charset=utf-8"):
        self._send_bytes(status, text.encode("utf-8", errors="replace"), content_type)

    def _send_json(self, status: int, data: dict):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, payload, "application/json; charset=utf-8")

    def _parse_request_body(self) -> tuple[bytes, str, dict | None, dict | None]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > MAX_BODY_BYTES:
            raise ValueError(f"Request body too large ({length} bytes)")
        body = self.rfile.read(length) if length > 0 else b""
        ctype = (self.headers.get("Content-Type", "") or "").lower()
        body_text = body.decode("utf-8", errors="replace")

        req_json = None
        req_form = None

        if "application/json" in ctype:
            try:
                req_json = json.loads(body_text) if body_text.strip() else None
            except Exception:
                req_json = None

        if "application/x-www-form-urlencoded" in ctype:
            try:
                qs2 = urllib.parse.parse_qs(body_text, keep_blank_values=True)
                req_form = {k: (v[0] if len(v) == 1 else v) for k, v in qs2.items()}
            except Exception:
                req_form = None

        return body, body_text, req_json, req_form

    def _handle_exec_api(self, project_root: str, req_json: dict | None, req_form: dict | None):
        payload = req_json if isinstance(req_json, dict) else (req_form if isinstance(req_form, dict) else {})
        code = payload.get("code", "")
        source_name = payload.get("path", "browser_demo.nc") or "browser_demo.nc"
        if not isinstance(code, str):
            self._send_json(400, {"ok": False, "error": "'code' muss ein String sein."})
            return
        if not code.strip():
            self._send_json(400, {"ok": False, "error": "Kein NC-Code gesendet."})
            return
        if len(code.encode("utf-8")) > MAX_CODE_BYTES:
            self._send_json(413, {"ok": False, "error": f"NC-Code ist zu groß (max {MAX_CODE_BYTES} Bytes)."})
            return
        blocked = _blocked_nc_text(code)
        if blocked:
            self._send_json(400, {"ok": False, "error": blocked})
            return
        try:
            output, meta = _run_nc_text_capture(code, project_root=project_root, source_name=str(source_name))
            self._send_json(200, {"ok": True, "output": output, "meta": meta})
        except Exception as e:
            self._send_json(500, {"ok": False, "error": f"NC ERROR: {e}"})

    def _handle_interactive_route(self, root: str, ip: str, dateiname: str):
        session: NCSession = self.server.nc_session
        ips = _load_ips(root)

        if ip not in ips:
            if ip == ALLOWED_IP:
                ips[ip] = {"datei": dateiname}
                _save_ips(root, ips)
            else:
                self._send_text(404, f"Datei {dateiname} für IP {ip} nicht gefunden!")
                return

        current_name = (ips.get(ip) or {}).get("datei", "")
        if current_name != dateiname:
            if ip == ALLOWED_IP:
                ips[ip]["datei"] = dateiname
                _save_ips(root, ips)
            else:
                self._send_text(404, f"Datei {dateiname} für IP {ip} nicht gefunden!")
                return

        if not session.current_process or session.current_process.poll() is not None or session.current_script != dateiname:
            err = _start_nc_script(session, root, dateiname, ip)
            if err:
                self._send_text(404, err)
                return

        html = INTERACTIVE_HTML.replace("__DATEINAME__", dateiname).replace("__IP__", ip).replace("__ALLOWED_IP__", ALLOWED_IP).replace("__PORT__", str(self.server.server_port))
        self._send_text(200, html, "text/html; charset=utf-8")

    def _handle(self):
        root = self.server.root_dir
        parsed = urllib.parse.urlparse(self.path)
        url_path = parsed.path or "/"

        try:
            body, body_text, req_json, req_form = self._parse_request_body()
        except ValueError as e:
            self._send_json(413, {"ok": False, "error": str(e)})
            return

        if url_path == "/__nc_playground" and self.command == "GET":
            self._send_bytes(200, PLAYGROUND_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return

        if url_path == "/__nc_exec__" and self.command == "POST":
            self._handle_exec_api(project_root=root, req_json=req_json, req_form=req_form)
            return

        if url_path == "/__nc_exec__" and self.command == "GET":
            self._send_json(200, {
                "ok": True,
                "name": "NC Browser Runner API",
                "method": "POST",
                "accepts": ["application/json", "application/x-www-form-urlencoded"],
                "fields": ["code", "path"],
                "max_code_bytes": MAX_CODE_BYTES,
            })
            return

        if url_path == "/get_output" and self.command == "GET":
            session: NCSession = self.server.nc_session
            self._send_text(200, session.get_output_text())
            return

        if url_path == "/get_history" and self.command == "GET":
            session: NCSession = self.server.nc_session
            self._send_json(200, session.get_history())
            return

        if url_path == "/input" and self.command == "POST":
            session: NCSession = self.server.nc_session
            text = ""
            if isinstance(req_form, dict):
                text = str(req_form.get("text", ""))
            elif body_text:
                text = body_text
            text = text.rstrip("\r\n")
            if text:
                session.add_history(text)
            proc = session.current_process
            if proc and proc.poll() is None and proc.stdin:
                try:
                    proc.stdin.write(text + "\n")
                    proc.stdin.flush()
                except Exception:
                    pass
            self._send_bytes(204, b"", "text/plain; charset=utf-8")
            return

        m_register = re.fullmatch(r"/register/([^/]+)/([^/]+)", url_path)
        if m_register and self.command in ("GET", "POST"):
            ip = urllib.parse.unquote(m_register.group(1))
            dateiname = urllib.parse.unquote(m_register.group(2))
            if not _safe_nc_filename(dateiname):
                self._send_text(400, "Nur .nc Dateien sind erlaubt.")
                return
            ips = _load_ips(root)
            ips[ip] = {"datei": dateiname}
            _save_ips(root, ips)
            self._send_text(200, f"IP {ip} registriert mit Datei {dateiname}")
            return

        m_ip = re.fullmatch(r"/ip/([^/]+)/([^/]+)", url_path)
        if m_ip and self.command == "GET":
            ip = urllib.parse.unquote(m_ip.group(1))
            dateiname = urllib.parse.unquote(m_ip.group(2))
            self._handle_interactive_route(root, ip, dateiname)
            return

        if url_path.startswith("/api/"):
            rel_fs = url_path.lstrip("/")
        else:
            rel_fs = os.path.join("www", url_path.lstrip("/"))

        try:
            full = _safe_join(root, rel_fs)
        except Exception:
            self.send_error(403)
            return

        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        query = {k: (v[0] if len(v) == 1 else v) for k, v in qs.items()}

        req_obj = {
            "method": self.command,
            "path": url_path,
            "query": query,
            "headers": {k: v for k, v in self.headers.items()},
            "body": body_text,
            "json": req_json,
            "form": req_form,
        }

        if os.path.isdir(full):
            idx = os.path.join(full, "index.html")
            if os.path.isfile(idx):
                full = idx
            else:
                self.send_error(404)
                return

        if full.lower().endswith(".nc") and os.path.isfile(full):
            try:
                status, headers, resp = _run_nc_file(full, req_obj, project_root=root)
                self._send_bytes(status, resp, headers.pop("Content-Type", "text/html; charset=utf-8"), headers)
            except Exception as e:
                self._send_bytes(500, ("NC ERROR: " + str(e)).encode("utf-8", errors="replace"))
            return

        if os.path.isfile(full):
            ctype2, _ = mimetypes.guess_type(full)
            if (ctype2 or "").startswith("text/") and "charset=" not in (ctype2 or ""):
                ctype2 = (ctype2 or "text/plain") + "; charset=utf-8"
            ctype2 = ctype2 or "application/octet-stream"
            try:
                with open(full, "rb") as f:
                    data = f.read()
                self._send_bytes(200, data, ctype2)
            except Exception:
                self.send_error(500)
            return

        self.send_error(404)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    host = DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    root = os.path.abspath(root)
    _ensure_uploads(root)
    _ensure_allowed_ip_registered(root)

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.root_dir = root
    httpd.nc_session = NCSession()

    print(f"NC server running: http://{host}:{port}/  (root={httpd.root_dir})")
    print("Routes: / -> www/, /api/* -> api/*")
    print("Extra: /__nc_playground + POST /__nc_exec__")
    print(f"Interactive: /ip/{ALLOWED_IP}/dein_script.nc")
    print(f"Uploads dir: {os.path.join(root, UPLOADS_DIRNAME)}")
    print("Data dir: _data/ (json.save/load)")

    try:
        httpd.serve_forever()
    finally:
        try:
            httpd.nc_session.stop_process()
        except Exception:
            pass


if __name__ == "__main__":
    main()
