#!/usr/bin/env python3
"""POST /kiss-tools/<name>. Basic KISS_GATEWAY_*; SaaS si KISS_SAAS_API_BASE_URL (ver saas_backend). Puerto KISS_GATEWAY_PORT."""
from __future__ import annotations

import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

_SRV_DIR = Path(__file__).resolve().parent
if str(_SRV_DIR) not in sys.path:
    sys.path.insert(0, str(_SRV_DIR))

import saas_backend  # noqa: E402

PORT = int(os.environ.get("KISS_GATEWAY_PORT", "9876"))
USER = os.environ.get("KISS_GATEWAY_USER", "demo")
PASSWORD = os.environ.get("KISS_GATEWAY_PASSWORD", "demo")
DISABLE_AUTH = os.environ.get("KISS_GATEWAY_DISABLE_AUTH", "").lower() in ("1", "true", "yes")

_PUBLIC = os.environ.get("KISS_RK_PUBLIC_BASE", "https://rkcompradores.alt-94.dev").rstrip("/")
def _prop_url(suffix: str = "1001") -> str:
    return f"{_PUBLIC}/propiedades/{suffix}"
def _json(handler: BaseHTTPRequestHandler, code: int, obj: dict[str, Any]) -> None:
    b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(b)))
    handler.end_headers()
    handler.wfile.write(b)
def _read_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    n = int(handler.headers.get("Content-Length") or 0)
    if n <= 0:
        return {}
    raw = handler.rfile.read(n)
    try:
        o = json.loads(raw.decode("utf-8"))
        return o if isinstance(o, dict) else {}
    except json.JSONDecodeError:
        return {}
def _auth_ok(handler: BaseHTTPRequestHandler) -> bool:
    if DISABLE_AUTH:
        return True
    auth = handler.headers.get("Authorization") or ""
    if not auth.startswith("Basic "):
        return False
    try:
        dec = base64.b64decode(auth[6:].strip()).decode("utf-8")
        u, _, p = dec.partition(":")
        return u == USER and p == PASSWORD
    except Exception:
        return False
def tool_search_properties(body: dict[str, Any]) -> dict[str, Any]:
    city = body.get("city") or "Oviedo"
    prop = {"ref": "RK-DEMO-1", "title": f"Piso demo en {city}", "city": city, "price": 189000, "bedrooms": 3, "url": _prop_url("1001")}
    return {"properties": [prop], "count": 1, "total": 1}
def tool_property_details(body: dict[str, Any]) -> dict[str, Any]:
    ref = str(body.get("ref") or "RK-DEMO-1")
    p = {"title": f"Detalle demo {ref}", "ref": ref, "city": "Oviedo", "price": 189000, "bedrooms": 3, "bathrooms": 2, "description": "Vivienda de demostración del gateway KISS.", "operation": "Venta", "url": _prop_url("1001")}
    return {"property": p, "has_agent": True, "agent_info": {"id": "42", "name": "Agente demo"}}
def tool_property_interest(body: dict[str, Any]) -> dict[str, Any]:
    idx, ext = body.get("property_index") or 1, body.get("external_id") or "454648"
    p = {"externalId": str(ext), "ref": "RK-DEMO-1", "title": f"Selección ordinal {idx}", "price": 189000, "url": _prop_url("1001")}
    return {"property": p, "has_agent": True, "agent_info": {"id": "42", "name": "Agente demo"}}
def tool_search_contact(body: dict[str, Any]) -> dict[str, Any]:
    tel = str(body.get("telefono") or "")
    return {"contactos": [{"id_contacto": "9001", "nombre": "Contacto demo", "telefono": tel}], "total": 1, "message": "ok (demo)"}
def tool_create_contact(body: dict[str, Any]) -> dict[str, Any]:
    return {"id_contacto": "9002", "id_usuario": "u-demo", "message": f"contacto creado: {body.get('nombre', '')}"}
def tool_create_demand(body: dict[str, Any]) -> dict[str, Any]:
    return {"id_demanda": "D-7001", "id_usuario": "u-demo", "message": f"demanda demo inmueble {body.get('id_inmueble', '')}"}
def tool_check_agent_availability(body: dict[str, Any]) -> dict[str, Any]:
    aid, d = str(body.get("agent_id") or "42"), str(body.get("date") or "2026-04-10")
    return {"agent_id": aid, "date": d, "available_slots": ["10:00", "11:00", "17:00"], "busy_slots": [], "total_slots": 3}
def tool_schedule_visit(body: dict[str, Any]) -> dict[str, Any]:
    return {"gestion_id": "G-5001", "property_id": str(body.get("property_external_id") or ""), "agent_id": str(body.get("agent_id") or ""), "date": str(body.get("date") or ""), "time": str(body.get("time") or ""), "status": "confirmed", "message": "visita agendada (demo)"}
def tool_cancel_visit(body: dict[str, Any]) -> dict[str, Any]:
    return {"gestion_id": str(body.get("gestion_id") or ""), "status": "cancelled", "message": "visita cancelada (demo)"}
DEMO_TOOLS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "search_properties": tool_search_properties,
    "property_details": tool_property_details,
    "property_interest": tool_property_interest,
    "search_contact": tool_search_contact,
    "create_contact": tool_create_contact,
    "create_demand": tool_create_demand,
    "check_agent_availability": tool_check_agent_availability,
    "schedule_visit": tool_schedule_visit,
    "cancel_visit": tool_cancel_visit,
}
def _run_tool(name: str, body: dict[str, Any]) -> dict[str, Any]:
    if saas_backend.configured():
        fn = saas_backend.TOOLS.get(name)
        if fn:
            return fn(body)
    demo = DEMO_TOOLS.get(name)
    if demo:
        return demo(body)
    raise KeyError(name)
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[gateway] {self.address_string()} - {fmt % args}")
    def do_GET(self) -> None:  # noqa: N802
        p = urlparse(self.path).path
        if p == "/health":
            mode = "saas" if saas_backend.configured() else "demo"
            return _json(self, 200, {"status": "ok", "mode": mode, "tools": list(DEMO_TOOLS.keys())})
        if p == "/":
            return _json(self, 200, {"service": "kiss_tool_gateway", "health": "/health"})
        self.send_error(404)
    def do_POST(self) -> None:  # noqa: N802
        p = urlparse(self.path).path
        if not p.startswith("/kiss-tools/"):
            return _json(self, 404, {"error": "not_found"})
        if not _auth_ok(self):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="kiss"')
            self.end_headers()
            return
        name = p.split("/")[-1].strip()
        if name not in DEMO_TOOLS:
            return _json(self, 404, {"error": "unknown_tool", "name": name})
        body = _read_body(self)
        try:
            out = _run_tool(name, body)
            return _json(self, 200, out)
        except Exception as e:
            return _json(self, 500, {"error": str(e)})
def main() -> None:
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    mode = "saas → " + (os.environ.get("KISS_SAAS_API_BASE_URL") or "").split("://", 1)[-1][:48]
    if not saas_backend.configured():
        mode = "demo (sin KISS_SAAS_API_BASE_URL)"
    print(
        f"KISS tool gateway http://127.0.0.1:{PORT} | {mode} | "
        f"Basic user={USER!r} DISABLE_AUTH={DISABLE_AUTH}"
    )
    srv.serve_forever()
if __name__ == "__main__":
    main()
