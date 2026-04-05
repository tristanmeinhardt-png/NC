import os
import sys
import re
import json
import mimetypes
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import nc

MAX_BODY_BYTES = 512_000
MAX_CODE_BYTES = 200_000
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080

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
      <div class="muted">Führt nur NC-Code aus. Keine Python-Bridge, kein Python-Upload, kein Python-Start.</div>
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
        <div class="small">Geblockt werden zusätzlich offensichtliche Python-Bridge-Aufrufe wie <code>import py</code>, <code>py.</code>, <code>import pkg</code> oder <code>import package</code>.</div>
        <div class="examples">
          <div class="hint"><strong>Route:</strong><br><code>GET /__nc_playground</code></div>
          <div class="hint"><strong>API:</strong><br><code>POST /__nc_exec__</code></div>
        </div>
      </div>
    </div>
  </div>

<script>
const STORAGE_KEY = 'nc_browser_runner_code_v2';
const PATH_KEY = 'nc_browser_runner_path_v2';
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
    import io
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


class Handler(BaseHTTPRequestHandler):
    server_version = "NCServer/1.4"

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

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.root_dir = os.path.abspath(root)

    print(f"NC server running: http://{host}:{port}/  (root={httpd.root_dir})")
    print("Routes: / -> www/, /api/* -> api/*")
    print("Extra: /__nc_playground + POST /__nc_exec__")
    print("Data dir: _data/ (json.save/load)")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
