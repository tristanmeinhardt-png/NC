import os
import sys
import json
import time
import base64
import secrets
import hashlib
import mimetypes
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# ----------------------------
# Utils
# ----------------------------

def _json_load(path, default):
  try:
    if not os.path.isfile(path):
      return default
    with open(path, "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return default

def _json_save(path, obj):
  os.makedirs(os.path.dirname(path), exist_ok=True)
  tmp = path + ".tmp"
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(obj, f, ensure_ascii=False, indent=2)
  os.replace(tmp, path)

def _send_json(h, status, obj):
  body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
  h.send_response(status)
  h.send_header("Content-Type", "application/json; charset=utf-8")
  h.send_header("Cache-Control", "no-store")
  # CORS optional (harmless for localhost)
  h.send_header("Access-Control-Allow-Origin", "*")
  h.send_header("Access-Control-Allow-Headers", "Content-Type")
  h.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
  h.send_header("Content-Length", str(len(body)))
  h.end_headers()
  h.wfile.write(body)

def _send_text(h, status, text, ctype="text/plain; charset=utf-8"):
  data = (text or "").encode("utf-8", errors="replace")
  h.send_response(status)
  h.send_header("Content-Type", ctype)
  h.send_header("Content-Length", str(len(data)))
  h.end_headers()
  h.wfile.write(data)

def _read_body_json(h):
  length = int(h.headers.get("Content-Length", "0") or "0")
  raw = h.rfile.read(length) if length > 0 else b""
  if not raw:
    return {}
  try:
    return json.loads(raw.decode("utf-8", errors="replace"))
  except Exception:
    return {}

def _cookie_parse(cookie_header: str):
  out = {}
  if not cookie_header:
    return out
  parts = cookie_header.split(";")
  for p in parts:
    if "=" in p:
      k, v = p.split("=", 1)
      out[k.strip()] = v.strip()
  return out

def _cookie_set(h, name, value, max_age=None):
  # HttpOnly session cookie
  # SameSite=Lax => funktioniert normal im Browser
  s = f"{name}={value}; Path=/; HttpOnly; SameSite=Lax"
  if max_age is not None:
    s += f"; Max-Age={int(max_age)}"
  h.send_header("Set-Cookie", s)

def _cookie_clear(h, name):
  h.send_header("Set-Cookie", f"{name}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")

def _hash_pw(password: str, salt_hex: str = None):
  salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
  dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
  return {"salt": salt.hex(), "hash": dk.hex()}

def _verify_pw(password: str, rec: dict):
  try:
    salt = bytes.fromhex(rec["salt"])
    want = rec["hash"]
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return dk.hex() == want
  except Exception:
    return False

def _safe_rel(path: str):
  # normalize, block traversal
  p = (path or "").replace("\\", "/").strip("/")
  p = os.path.normpath(p).replace("\\", "/")
  if p == ".":
    p = ""
  if p.startswith("../") or p.startswith("..\\") or p == ".." or "/.." in p or ".." in p.split("/"):
    raise ValueError("blocked path traversal")
  return p

def _join_user_cloud(root, username, relpath):
  rel = _safe_rel(relpath)
  base = os.path.join(root, "_cloud", username)
  full = os.path.abspath(os.path.join(base, rel))
  base_abs = os.path.abspath(base)
  if not (full == base_abs or full.startswith(base_abs + os.sep)):
    raise ValueError("blocked path")
  return base, full

def _fmt_item(path_abs, base_abs, is_dir):
  st = os.stat(path_abs)
  rel = os.path.relpath(path_abs, base_abs).replace("\\", "/")
  if rel == ".":
    rel = ""
  name = os.path.basename(path_abs) if rel else ""
  return {
    "name": name,
    "path": rel,
    "type": "dir" if is_dir else "file",
    "size": 0 if is_dir else int(st.st_size),
    "mtime": int(st.st_mtime * 1000),
  }

def _b64_chunks_from_file(fp, chunk_bytes=200_000):
  # returns list[str] of base64 chunks
  chunks = []
  with open(fp, "rb") as f:
    while True:
      b = f.read(chunk_bytes)
      if not b:
        break
      chunks.append(base64.b64encode(b).decode("ascii"))
  return chunks

# ----------------------------
# Server
# ----------------------------

class Handler(BaseHTTPRequestHandler):
  server_version = "TCloudNC/2.0"

  def do_OPTIONS(self):
    self.send_response(204)
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
    self.end_headers()

  def do_GET(self):
    self._handle()

  def do_POST(self):
    self._handle()

  def _handle(self):
    root = self.server.root_dir

    data_dir = os.path.join(root, "_data")
    users_p = os.path.join(data_dir, "users.json")
    sess_p  = os.path.join(data_dir, "sessions.json")
    share_p = os.path.join(data_dir, "shares.json")
    os.makedirs(data_dir, exist_ok=True)

    users = _json_load(users_p, {"users": []})
    sessions = _json_load(sess_p, {"sessions": {}})
    shares = _json_load(share_p, {"shares": {}})

    parsed = urllib.parse.urlparse(self.path)
    path = parsed.path or "/"
    qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    q = {k: (v[0] if len(v) == 1 else v) for k, v in qs.items()}

    # auth via cookie
    cookies = _cookie_parse(self.headers.get("Cookie", ""))
    sid = cookies.get("tcloud_sid")
    sess = sessions["sessions"].get(sid) if sid else None
    username = sess.get("username") if isinstance(sess, dict) else None

    def find_user(u):
      for x in users["users"]:
        if x.get("username") == u:
          return x
      return None

    def is_admin(u):
      usr = find_user(u)
      return bool(usr and usr.get("is_admin"))

    # -------------------------
    # API: /api/*.nc
    # -------------------------

    # NOTE: IMPORTANT for your old app.js:
    # /api/me.nc MUST return 200 even when not logged in.
    if path == "/api/me.nc":
      if not username:
        return _send_json(self, 200, {"logged_in": False})
      usr = find_user(username)
      return _send_json(self, 200, {
        "logged_in": True,
        "username": username,
        "is_admin": bool(usr and usr.get("is_admin")),
      })

    if path == "/api/register.nc":
      body = _read_body_json(self)
      u = (body.get("username") or "").strip()
      p = (body.get("password") or "")
      if not u or not p:
        return _send_json(self, 400, {"error": "username/password fehlen"})

      if find_user(u):
        return _send_json(self, 409, {"error": "User existiert bereits"})

      # first account becomes admin
      first = (len(users["users"]) == 0)
      users["users"].append({
        "username": u,
        "pw": _hash_pw(p),
        "is_admin": first,
        "quota": 0,  # 0 = unlimited by default (you can change later)
      })
      _json_save(users_p, users)
      return _send_json(self, 200, {"ok": True})

    if path == "/api/login.nc":
      body = _read_body_json(self)
      u = (body.get("username") or "").strip()
      p = (body.get("password") or "")
      usr = find_user(u)
      if (not usr) or (not _verify_pw(p, usr.get("pw", {}))):
        return _send_json(self, 401, {"error": "login failed"})

      # create session
      sid_new = secrets.token_urlsafe(32)
      sessions["sessions"][sid_new] = {
        "username": u,
        "ts": int(time.time() * 1000),
      }
      _json_save(sess_p, sessions)

      self.send_response(200)
      _cookie_set(self, "tcloud_sid", sid_new, max_age=60*60*24*7)  # 7 days
      self.send_header("Content-Type", "application/json; charset=utf-8")
      self.send_header("Cache-Control", "no-store")
      self.end_headers()
      self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8"))
      return

    if path == "/api/logout.nc":
      # delete session cookie + session record
      if sid and sid in sessions["sessions"]:
        del sessions["sessions"][sid]
        _json_save(sess_p, sessions)

      self.send_response(200)
      _cookie_clear(self, "tcloud_sid")
      self.send_header("Content-Type", "application/json; charset=utf-8")
      self.end_headers()
      self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8"))
      return

    # from here: must be logged in (except share)
    if path.startswith("/api/") and path not in ("/api/share.nc",):
      if not username:
        return _send_json(self, 401, {"error": "not logged in"})

    # ---------- Cloud ops ----------
    if path == "/api/list.nc":
      rel = q.get("path", "") or ""
      try:
        base, full = _join_user_cloud(root, username, rel)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})

      os.makedirs(base, exist_ok=True)
      os.makedirs(full, exist_ok=True)

      items = []
      try:
        for name in sorted(os.listdir(full), key=lambda s: s.lower()):
          p = os.path.join(full, name)
          is_dir = os.path.isdir(p)
          it = _fmt_item(p, base, is_dir)
          # fix name for root listings
          it["name"] = name
          items.append(it)
      except Exception as e:
        return _send_json(self, 500, {"error": str(e)})

      # response expects data.path + items
      # path should be rel normalized
      try:
        rel_norm = _safe_rel(rel)
      except Exception:
        rel_norm = ""
      return _send_json(self, 200, {"path": rel_norm, "items": items})

    if path == "/api/mkdir.nc":
      body = _read_body_json(self)
      rel = (body.get("path") or "").strip()
      try:
        base, full = _join_user_cloud(root, username, rel)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})
      try:
        os.makedirs(full, exist_ok=True)
        return _send_json(self, 200, {"ok": True})
      except Exception as e:
        return _send_json(self, 500, {"error": str(e)})

    if path == "/api/rename.nc":
      body = _read_body_json(self)
      oldp = (body.get("old_path") or "").strip()
      newp = (body.get("new_path") or "").strip()
      try:
        base, old_full = _join_user_cloud(root, username, oldp)
        _base2, new_full = _join_user_cloud(root, username, newp)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})
      try:
        os.makedirs(os.path.dirname(new_full), exist_ok=True)
        os.replace(old_full, new_full)
        return _send_json(self, 200, {"ok": True})
      except Exception as e:
        return _send_json(self, 500, {"error": str(e)})

    if path == "/api/delete.nc":
      body = _read_body_json(self)
      rel = (body.get("path") or "").strip()
      try:
        base, full = _join_user_cloud(root, username, rel)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})
      try:
        if os.path.isdir(full):
          # delete dir recursively
          for rootp, dirs, files in os.walk(full, topdown=False):
            for fn in files:
              os.remove(os.path.join(rootp, fn))
            for dn in dirs:
              os.rmdir(os.path.join(rootp, dn))
          os.rmdir(full)
        else:
          os.remove(full)
        return _send_json(self, 200, {"ok": True})
      except FileNotFoundError:
        return _send_json(self, 404, {"error": "not found"})
      except Exception as e:
        return _send_json(self, 500, {"error": str(e)})

    if path == "/api/upload.nc":
      body = _read_body_json(self)
      rel_dir = (body.get("path") or "").strip()   # current dir
      name = (body.get("name") or "").strip()
      b64 = body.get("b64") or ""
      mime = (body.get("mime") or "application/octet-stream").strip()
      overwrite = bool(body.get("overwrite"))

      if not name:
        return _send_json(self, 400, {"error": "missing name"})
      # block weird names
      if "/" in name or "\\" in name or name in (".", ".."):
        return _send_json(self, 400, {"error": "bad filename"})

      try:
        base, dir_full = _join_user_cloud(root, username, rel_dir)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})

      os.makedirs(dir_full, exist_ok=True)
      fp = os.path.join(dir_full, name)
      if (not overwrite) and os.path.exists(fp):
        return _send_json(self, 409, {"error": "file exists (overwrite=false)"})

      try:
        raw = base64.b64decode(b64.encode("ascii"), validate=False)
      except Exception:
        return _send_json(self, 400, {"error": "bad base64"})

      try:
        with open(fp, "wb") as f:
          f.write(raw)
        # store meta sidecar (optional)
        meta = {"mime": mime, "size": len(raw), "mtime": int(time.time()*1000)}
        _json_save(fp + ".meta.json", meta)
        return _send_json(self, 200, {"ok": True})
      except Exception as e:
        return _send_json(self, 500, {"error": str(e)})

    # download: meta + chunks
    # app.js expects:
    #   GET /api/file_meta.nc?path=...
    #   GET /api/file_chunk.nc?id=...&i=...
    if path == "/api/file_meta.nc":
      rel = q.get("path", "") or ""
      try:
        base, full = _join_user_cloud(root, username, rel)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})

      if not os.path.isfile(full):
        return _send_json(self, 404, {"error": "not found"})

      # create an ID in memory mapping in sessions.json (simple & persistent)
      # we store file mappings under sessions["files"][sid]
      if not sid:
        return _send_json(self, 401, {"error": "no session"})
      sessions = _json_load(sess_p, {"sessions": {}})
      srec = sessions["sessions"].get(sid)
      if not isinstance(srec, dict):
        return _send_json(self, 401, {"error": "no session"})
      srec.setdefault("files", {})
      fid = secrets.token_urlsafe(16)
      srec["files"][fid] = {"path": rel, "ts": int(time.time()*1000)}
      sessions["sessions"][sid] = srec
      _json_save(sess_p, sessions)

      ctype, _ = mimetypes.guess_type(full)
      ctype = ctype or "application/octet-stream"

      # size -> estimate chunks: chunk_bytes base64 will inflate; but we chunk raw bytes
      st = os.stat(full)
      chunk_bytes = 200_000
      chunks = (st.st_size + chunk_bytes - 1) // chunk_bytes

      meta = {
        "id": fid,
        "name": os.path.basename(full),
        "mime": ctype,
        "size": int(st.st_size),
        "chunks": int(chunks),
      }
      return _send_json(self, 200, {"meta": meta})

    if path == "/api/file_chunk.nc":
      if not sid:
        return _send_json(self, 401, {"error": "no session"})
      fid = (q.get("id") or "").strip()
      idx = int(q.get("i") or 0)

      sessions = _json_load(sess_p, {"sessions": {}})
      srec = sessions["sessions"].get(sid)
      if not isinstance(srec, dict):
        return _send_json(self, 401, {"error": "no session"})
      fmap = (srec.get("files") or {})
      frec = fmap.get(fid)
      if not isinstance(frec, dict):
        return _send_json(self, 404, {"error": "bad id"})
      rel = frec.get("path") or ""

      try:
        base, full = _join_user_cloud(root, username, rel)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})
      if not os.path.isfile(full):
        return _send_json(self, 404, {"error": "not found"})

      chunk_bytes = 200_000
      try:
        with open(full, "rb") as f:
          f.seek(idx * chunk_bytes)
          raw = f.read(chunk_bytes)
        b64 = base64.b64encode(raw).decode("ascii")
        return _send_json(self, 200, {"b64": b64})
      except Exception as e:
        return _send_json(self, 500, {"error": str(e)})

    # share
    if path == "/api/share_create.nc":
      body = _read_body_json(self)
      rel = (body.get("path") or "").strip()
      ttl_ms = int(body.get("ttl_ms") or 3600000)

      # must exist
      try:
        base, full = _join_user_cloud(root, username, rel)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})
      if not os.path.exists(full):
        return _send_json(self, 404, {"error": "not found"})

      token = secrets.token_urlsafe(24)
      shares["shares"][token] = {
        "owner": username,
        "path": rel,
        "exp": int(time.time()*1000) + max(10_000, ttl_ms),
      }
      _json_save(share_p, shares)
      return _send_json(self, 200, {"ok": True, "token": token})

    if path == "/api/share.nc":
      token = (q.get("token") or "").strip()
      rec = shares["shares"].get(token)
      if not isinstance(rec, dict):
        return _send_json(self, 404, {"error": "bad token"})
      if int(time.time()*1000) > int(rec.get("exp") or 0):
        return _send_json(self, 410, {"error": "expired"})

      owner = rec.get("owner")
      rel = rec.get("path") or ""
      try:
        base, full = _join_user_cloud(root, owner, rel)
      except Exception:
        return _send_json(self, 400, {"error": "bad path"})
      if not os.path.isfile(full):
        return _send_json(self, 404, {"error": "not found"})

      # send as file download (not chunked)
      ctype, _ = mimetypes.guess_type(full)
      ctype = ctype or "application/octet-stream"
      try:
        with open(full, "rb") as f:
          data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(full)}"')
        self.end_headers()
        self.wfile.write(data)
        return
      except Exception as e:
        return _send_json(self, 500, {"error": str(e)})

    # admin
    if path == "/api/admin_users.nc":
      if not username or not is_admin(username):
        return _send_json(self, 403, {"error": "admin only"})
      safe = []
      for u in users["users"]:
        safe.append({
          "username": u.get("username"),
          "is_admin": bool(u.get("is_admin")),
          "quota": int(u.get("quota") or 0),
        })
      return _send_json(self, 200, {"users": safe})

    if path == "/api/admin_set_quota.nc":
      if not username or not is_admin(username):
        return _send_json(self, 403, {"error": "admin only"})
      body = _read_body_json(self)
      u = (body.get("username") or "").strip()
      qv = int(body.get("quota") or 0)
      usr = find_user(u)
      if not usr:
        return _send_json(self, 404, {"error": "user not found"})
      usr["quota"] = max(0, qv)
      _json_save(users_p, users)
      return _send_json(self, 200, {"ok": True})

    # unknown api -> 404
    if path.startswith("/api/"):
      return _send_json(self, 404, {"error": "unknown api"})

    # -------------------------
    # Static files (index.html, /static/*, etc.)
    # -------------------------
    req_path = path
    if req_path == "/":
      req_path = "/index.html"
    fs_path = os.path.abspath(os.path.join(root, req_path.lstrip("/")))
    root_abs = os.path.abspath(root)
    if not (fs_path == root_abs or fs_path.startswith(root_abs + os.sep)):
      return self.send_error(403)

    if os.path.isdir(fs_path):
      idx = os.path.join(fs_path, "index.html")
      if os.path.isfile(idx):
        fs_path = idx
      else:
        return self.send_error(404)

    if not os.path.isfile(fs_path):
      return self.send_error(404)

    ctype, _ = mimetypes.guess_type(fs_path)
    ctype = ctype or "application/octet-stream"
    try:
      with open(fs_path, "rb") as f:
        data = f.read()
      self.send_response(200)
      self.send_header("Content-Type", ctype)
      self.send_header("Content-Length", str(len(data)))
      self.end_headers()
      self.wfile.write(data)
    except Exception:
      self.send_error(500)

def main():
  root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
  port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

  root = os.path.abspath(root)
  os.makedirs(os.path.join(root, "_data"), exist_ok=True)
  os.makedirs(os.path.join(root, "_cloud"), exist_ok=True)

  httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
  httpd.root_dir = root
  print(f"Server läuft: http://127.0.0.1:{port}/  (root={root})")
  httpd.serve_forever()

if __name__ == "__main__":
  main()
