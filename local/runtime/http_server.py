import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from model_adapter import call_model
from run import run, tick_run_fn
from tick import tick_all


def default_agents_root() -> Path:
    return Path(e).resolve() if (e := os.environ.get("KISS_AGENTS_ROOT")) else (
        Path(__file__).resolve().parent.parent / "examples"
    ).resolve()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", "0"))
        if n > 1_000_000:
            raise ValueError("body too large")
        return json.loads((self.rfile.read(n) if n else b"{}").decode("utf-8") or "{}")

    def _send(self, code: int, obj: dict) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"ok": True}) if self.path == "/health" else self.send_error(404)

    def do_POST(self):
        try:
            if self.path == "/api/run":
                b = self._read_json()
                root = default_agents_root()
                aid, pr = str(b.get("agent_id", "")).strip(), str(b.get("prompt", ""))
                folder = root / aid
                if not aid or not folder.is_dir():
                    return self._send(400, {"ok": False, "error": "bad agent_id"})
                for rel, content in (b.get("docs") or {}).items():
                    rel = str(rel)
                    if ".." in rel or rel.startswith(("/", "\\")):
                        return self._send(400, {"ok": False, "error": "bad path"})
                    p = folder / rel
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(str(content), encoding="utf-8")
                self._send(200, {"ok": True, "message": run(folder, pr, call_model)})
            elif self.path == "/api/tick":
                root = default_agents_root()
                self._send(200, {"ok": True, "runs": tick_all(root, tick_run_fn(root, call_model))})
            else:
                self.send_error(404)
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    httpd = HTTPServer((host, int(port)), Handler)
    print(f"KISS Agents http://{host}:{port}  (POST /api/run /api/tick, GET /health)")
    httpd.serve_forever()
