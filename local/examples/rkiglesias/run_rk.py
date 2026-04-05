#!/usr/bin/env python3
"""MaRK: Chat Completions + 9 tools HTTP → gateway; usa md_io/kiss-write del runtime KISS.
Uso: export KISS_HTTP_TOOL_BASE_URL=… USER/PASSWORD o BEARER, OPENAI_API_KEY; python3 run_rk.py "…"
Opcional: KISS_HTTP_TOOL_TIMEOUT, KISS_OPENAI_CHAT_MODEL."""
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_AGENT_DIR = Path(__file__).resolve().parent
def _find_kiss_runtime(start: Path) -> Path:
    cur = start
    for _ in range(8):
        cand = cur / "runtime"
        if (cand / "md_io.py").is_file():
            return cand
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError(
        "No se encontró KISS local/runtime (md_io.py). "
        "Coloca este agente bajo .../KISS Agents/local/examples/ o ajusta la ruta."
    )
try:
    _RUNTIME = _find_kiss_runtime(_AGENT_DIR)
except RuntimeError as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
sys.path.insert(0, str(_RUNTIME))

import md_io  # noqa: E402
import llm as kiss_llm  # noqa: E402
def _post_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    r = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenAI HTTP {e.code}: {e.read().decode(errors='replace')}") from e
def _http_tool_timeout() -> float:
    try:
        return float(os.environ.get("KISS_HTTP_TOOL_TIMEOUT", "180"))
    except ValueError:
        return 180.0
def _http_tool_exec(base: str, name: str, arguments: dict[str, Any], h: dict[str, str]) -> str:
    if os.environ.get("KISS_HTTP_TOOL_DEBUG", "").lower() in ("1", "true", "yes"):
        snippet = json.dumps(arguments or {}, ensure_ascii=False)[:240]
        print(f"[kiss-tool] {name} {snippet}", file=sys.stderr, flush=True)
    url = base.rstrip("/") + "/kiss-tools/" + name
    req = urllib.request.Request(url, data=json.dumps(arguments or {}).encode("utf-8"), headers={**h, "Content-Type": "application/json"}, method="POST")
    to = _http_tool_timeout()
    try:
        with urllib.request.urlopen(req, timeout=to) as resp:
            return resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return json.dumps(
            {"ok": False, "error": f"HTTP {e.code}", "body": e.read().decode(errors="replace")}
        )
    except socket.timeout:
        return json.dumps(
            {
                "ok": False,
                "error": "timeout",
                "hint": f"El gateway no respondió en {to:.0f}s. Sube KISS_HTTP_TOOL_TIMEOUT o "
                "KISS_SAAS_HTTP_TIMEOUT en el gateway si la API remota es lenta.",
            }
        )
    except urllib.error.URLError as e:
        return json.dumps({"ok": False, "error": "url_error", "reason": str(e.reason)})
def _load_saas_tools(agent_dir: Path) -> list[dict[str, Any]]:
    p = agent_dir / "input" / "saas_property_search_tools.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("tools") or [])
def _openai_parameters(input_schema: dict[str, Any]) -> dict[str, Any]:
    props: dict[str, Any] = {}
    req: list[str] = []
    for key, spec in input_schema.items():
        if not isinstance(spec, dict):
            continue
        entry = {k: v for k, v in spec.items() if k != "required"}
        if entry.get("type") == "array" and "items" not in entry:
            entry["items"] = {"type": "string"}
        props[key] = entry
        if spec.get("required"):
            req.append(key)
    return {"type": "object", "properties": props, "required": req}
def _build_openai_tools(tool_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in tool_rows:
        name = str(t.get("name", "")).strip()
        if not name:
            continue
        desc = str(t.get("description", "")).strip()
        schema = t.get("input_schema") if isinstance(t.get("input_schema"), dict) else {}
        out.append({"type": "function", "function": {"name": name, "description": desc[:4096], "parameters": _openai_parameters(schema)}})
    return out
def _auth_headers() -> dict[str, str]:
    h: dict[str, str] = {}
    tok = os.environ.get("KISS_HTTP_TOOL_BEARER", "").strip()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
        return h
    u = os.environ.get("KISS_HTTP_TOOL_USER", "").strip()
    pw = os.environ.get("KISS_HTTP_TOOL_PASSWORD", "").strip()
    if u or pw:
        b = base64.b64encode(f"{u}:{pw}".encode()).decode("ascii")
        h["Authorization"] = f"Basic {b}"
    return h
def run_once(agent_dir: Path, prompt: str) -> dict[str, Any]:
    base = (os.environ.get("KISS_HTTP_TOOL_BASE_URL") or "").strip().rstrip("/")
    if not base:
        raise RuntimeError(
            "Falta KISS_HTTP_TOOL_BASE_URL. Arranca el gateway: python3 server/kiss_tool_gateway.py"
        )
    tool_rows = _load_saas_tools(agent_dir)
    if not tool_rows:
        raise RuntimeError("Falta input/saas_property_search_tools.json")
    oai_tools = _build_openai_tools(tool_rows)
    model = (
        os.environ.get("KISS_OPENAI_CHAT_MODEL")
        or os.environ.get("OPENAI_MODEL")
        or "gpt-4o-mini"
    ).strip()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Falta OPENAI_API_KEY")
    base_sys = (
        os.environ.get("KISS_OPENAI_INSTRUCTIONS", "").strip()
        or "Eres MaRK; usa las herramientas cuando necesites datos."
    )
    sys = f"{base_sys}\n\n{kiss_llm._KISS_FILE_HINT}"
    ctx = md_io.load_agent(agent_dir)
    user_body = f"{ctx}\n\n---\n\nUSER_PROMPT:\n{prompt}"
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user_body},
    ]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    auth_tool = _auth_headers()
    max_rounds = int(os.environ.get("KISS_HTTP_TOOL_MAX_ROUNDS", "24"))
    last_text = ""
    for _ in range(max_rounds):
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": oai_tools,
            "tool_choice": "auto",
        }
        resp = _post_json("https://api.openai.com/v1/chat/completions", body, headers)
        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        last_text = (msg.get("content") or last_text or "").strip()
        calls = msg.get("tool_calls") or []
        if not calls:
            break
        messages.append(msg)
        for tc in calls:
            if tc.get("type") != "function":
                continue
            fn = tc.get("function") or {}
            tname = str(fn.get("name", "")).strip()
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                args = {}
            out = _http_tool_exec(base, tname, args, auth_tool)
            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": out[:80000]})
    text = last_text or "(sin texto final del modelo)"
    writes, display = kiss_llm._kiss_writes_bundle(text, "openai-http")
    try:
        cap = max(500, int(os.environ.get("KISS_REPLY_MAX_CHARS", "16000").strip()))
    except ValueError:
        cap = 16000
    return {"final": True, "message": display[:cap], "writes": writes}
def main() -> None:
    ap = argparse.ArgumentParser(description="MaRK + tools HTTP (carpeta del agente)")
    ap.add_argument("prompt", help="Instrucción del usuario")
    ap.add_argument(
        "--dir",
        type=Path,
        default=_AGENT_DIR,
        help="Carpeta del agente (por defecto: donde está este script)",
    )
    a = ap.parse_args()
    folder = Path(a.dir).resolve()
    try:
        r = run_once(folder, a.prompt)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    md_io.apply_writes(folder, r.get("writes") or [])
    print(r.get("message", "done"))
if __name__ == "__main__":
    main()
