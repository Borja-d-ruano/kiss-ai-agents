#!/usr/bin/env python3
"""Sirve el Finder (HTML/CSS/JS) + API mínima: listar, leer y subir (PUT). stdlib solamente."""
from __future__ import annotations
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
MAX_READ = 2_000_000
MAX_PUT = 50_000_000


def agents_root() -> Path:
    e = os.environ.get("KISS_AGENTS_ROOT", "").strip()
    if e:
        return Path(e).resolve()
    return (HERE.parent.parent / "local" / "examples").resolve()


def safe_child(root: Path, rel: str) -> Path | None:
    rel = (rel or "").strip().replace("\\", "/")
    if rel.startswith("/") or any(p == ".." for p in rel.split("/") if p):
        return None
    p = (root / rel).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return None
    return p


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        return

    def _send(self, code: int, body: bytes | str, ctype: str) -> None:
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _send_json(self, code: int, obj: object) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        u = urlparse(self.path)
        path = u.path
        if path in ("/", "/index.html"):
            self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if path in ("/style.css", "/app.js"):
            p = HERE / path.lstrip("/")
            if p.is_file():
                ct = "text/css; charset=utf-8" if path.endswith(".css") else "application/javascript; charset=utf-8"
                self._send(200, p.read_bytes(), ct)
            else:
                self.send_error(404)
            return
        root = agents_root()
        if path == "/api/list":
            rel = unquote(parse_qs(u.query).get("path", [""])[0])
            t = safe_child(root, rel)
            if t is None or not t.is_dir():
                self._send(400, "bad path", "text/plain; charset=utf-8")
                return
            entries = []
            for ch in sorted(t.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                entries.append(
                    {"name": ch.name, "kind": "dir" if ch.is_dir() else "file", "size": 0 if ch.is_dir() else ch.stat().st_size}
                )
            self._send_json(200, {"entries": entries})
            return
        if path == "/api/raw":
            rel = unquote(parse_qs(u.query).get("path", [""])[0])
            t = safe_child(root, rel)
            if t is None or not t.is_file():
                self._send(400, "bad path", "text/plain; charset=utf-8")
                return
            if t.stat().st_size > MAX_READ:
                self._send(400, "file too large", "text/plain; charset=utf-8")
                return
            self._send(200, t.read_bytes(), "text/plain; charset=utf-8")
            return
        self.send_error(404)

    def do_PUT(self) -> None:
        u = urlparse(self.path)
        if u.path != "/api/raw":
            self.send_error(404)
            return
        root = agents_root()
        rel = unquote(parse_qs(u.query).get("path", [""])[0])
        if not rel:
            self._send(400, "missing path", "text/plain; charset=utf-8")
            return
        t = safe_child(root, rel)
        if t is None:
            self._send(400, "bad path", "text/plain; charset=utf-8")
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n > MAX_PUT:
            self._send(400, "body too large", "text/plain; charset=utf-8")
            return
        raw = self.rfile.read(n) if n else b""
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(raw)
        self._send(200, "ok", "text/plain; charset=utf-8")


def main() -> None:
    host = os.environ.get("AGENTS_FINDER_HOST", "127.0.0.1")
    port = int(os.environ.get("AGENTS_FINDER_PORT", "9393"))
    r = agents_root()
    print(f"KISS agents-finder  http://{host}:{port}/")
    print(f"  KISS_AGENTS_ROOT={r}")
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
