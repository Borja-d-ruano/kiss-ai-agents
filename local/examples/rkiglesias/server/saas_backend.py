"""HTTP client al SaaS (property_search). Requiere KISS_SAAS_API_BASE_URL; token KISS_SAAS_API_TOKEN o KISS_SAAS_USE_X_API_TOKEN=1."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_DEFAULT_TIMEOUT = int(os.environ.get("KISS_SAAS_HTTP_TIMEOUT", "120"))
_PUBLIC_BASE = os.environ.get("KISS_RK_PUBLIC_BASE", "https://rkcompradores.alt-94.dev").rstrip("/")
_EP_PROPERTIES = os.environ.get("KISS_SAAS_ENDPOINT_PROPERTIES", "/api/properties")
_EP_PROP_SEARCH = os.environ.get("KISS_SAAS_ENDPOINT_PROPERTY_SEARCH", "/api/properties/search")
_EP_CONTACT_SEARCH = os.environ.get("KISS_SAAS_ENDPOINT_CONTACT_SEARCH", "/api/contactos/search")
_EP_CONTACT_CREATE = os.environ.get("KISS_SAAS_ENDPOINT_CONTACT_CREATE", "/api/contactos/create")
_EP_DEMANDS = os.environ.get("KISS_SAAS_ENDPOINT_DEMANDS", "/api/demands")
_EP_GESTIONES = os.environ.get("KISS_SAAS_ENDPOINT_GESTIONES", "/api/gestiones")
_EP_GESTION_CREATE = os.environ.get("KISS_SAAS_ENDPOINT_GESTION_CREATE", "/api/gestiones/create")
_EP_GESTION_DELETE = os.environ.get("KISS_SAAS_ENDPOINT_GESTION_DELETE", "/api/gestiones/delete")
def configured() -> bool:
    return bool((os.environ.get("KISS_SAAS_API_BASE_URL") or "").strip())
def _base() -> str:
    b = (os.environ.get("KISS_SAAS_API_BASE_URL") or "").strip().rstrip("/")
    if not b:
        raise RuntimeError("KISS_SAAS_API_BASE_URL no está definida")
    return b
def _token() -> str:
    return (os.environ.get("KISS_SAAS_API_TOKEN") or "").strip()
def _auth_headers() -> dict[str, str]:
    tok = _token()
    if not tok:
        return {}
    if os.environ.get("KISS_SAAS_USE_X_API_TOKEN", "").lower() in ("1", "true", "yes"):
        return {"X-API-Token": tok}
    hname = (os.environ.get("KISS_SAAS_AUTH_HEADER") or "Authorization").strip()
    prefix = (os.environ.get("KISS_SAAS_TOKEN_PREFIX") or "Bearer").strip()
    if prefix:
        return {hname: f"{prefix} {tok}"}
    return {hname: tok}
def _request(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    base = _base()
    url = base + path
    if query:
        flat: dict[str, str] = {}
        for k, v in query.items():
            if v is None:
                continue
            if isinstance(v, bool):
                flat[k] = "true" if v else "false"
            else:
                flat[k] = str(v)
        qs = urllib.parse.urlencode(flat)
        url = f"{url}?{qs}"
    headers = dict(_auth_headers())
    data = None
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        headers.setdefault("Content-Type", "application/json; charset=utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"SaaS HTTP {e.code}: {body[:2000]}") from e
def _find_id(obj: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        for v in obj.values():
            r = _find_id(v, keys)
            if r:
                return r
    elif isinstance(obj, list):
        for x in obj:
            r = _find_id(x, keys)
            if r:
                return r
    return None
def _parse_property_search_list(data: dict[str, Any]) -> tuple[list[dict[str, Any]], int, int]:
    properties: list[dict[str, Any]] = []
    total = 0
    if "data" in data and isinstance(data["data"], dict) and "docs" in data["data"]:
        properties = list(data["data"]["docs"] or [])
        total = int(data["data"].get("totalDocs") or len(properties))
    elif isinstance(data.get("properties"), list):
        properties = list(data["properties"])
        total = int(data.get("total") or len(properties))
    elif isinstance(data, list):
        properties = data
        total = len(properties)
    return properties, len(properties), total
def _enrich_listing(p: dict[str, Any]) -> dict[str, Any]:
    loc = p.get("location") or {}
    if loc:
        p.setdefault("city", loc.get("city") or loc.get("population"))
        p.setdefault("province", loc.get("province"))
        p.setdefault("zone", loc.get("zone"))
    pd = p.get("propertyDetails") or {}
    if pd:
        p.setdefault("bedrooms", pd.get("bedrooms"))
        p.setdefault("bathrooms", pd.get("bathrooms"))
        p.setdefault("surface", pd.get("surfaceAreaSqm"))
    if p.get("isManagedByIagestion"):
        ag = p.get("agent") or {}
        aid = p.get("agentId")
        name = f"{ag.get('nombre') or ''} {ag.get('apellidos') or ''}".strip()
        if aid and name:
            p["agent"] = {
                "id": str(aid),
                "name": name,
                "phone": ag.get("movil") or ag.get("telefono") or "N/A",
                "email": ag.get("email") or "N/A",
                "has_agent": True,
            }
    return p
def _listing_summary(p: dict[str, Any]) -> dict[str, Any]:
    p = _enrich_listing(dict(p))
    ext = p.get("externalId")
    if not ext and isinstance(p.get("source"), dict):
        ext = p["source"].get("externalId")
    ref = str(p.get("ref") or ext or p.get("id") or "")
    url = p.get("url")
    if not url and ref:
        url = f"{_PUBLIC_BASE}/propiedades/{ref}"
    return {
        "ref": ref,
        "externalId": ext,
        "title": p.get("title"),
        "city": p.get("city"),
        "province": p.get("province"),
        "price": p.get("price"),
        "bedrooms": p.get("bedrooms"),
        "bathrooms": p.get("bathrooms"),
        "operation": p.get("operation"),
        "propertyType": p.get("propertyType"),
        "url": url,
        "agent": p.get("agent"),
    }
def search_properties(body: dict[str, Any]) -> dict[str, Any]:
    q: dict[str, Any] = {}
    if body.get("city"):
        q["city"] = body["city"]
    if body.get("province"):
        q["province"] = body["province"]
    pt = body.get("property_type")
    if pt:
        q["propertyTypes"] = pt if isinstance(pt, str) else ",".join(str(x) for x in pt)
    op = body.get("operation")
    if op:
        q["operations"] = op if isinstance(op, str) else ",".join(str(x) for x in op)
    if body.get("bedrooms") is not None:
        q["bedrooms"] = str(body["bedrooms"])
    if body.get("bathrooms") is not None:
        q["bathrooms"] = str(body["bathrooms"])
    if body.get("min_price") is not None:
        q["minPrice"] = body["min_price"]
    if body.get("max_price") is not None:
        q["maxPrice"] = body["max_price"]
    feat = body.get("features")
    if feat:
        q["features"] = ",".join(str(x) for x in feat) if isinstance(feat, list) else str(feat)
    q["limit"] = int(os.environ.get("KISS_SAAS_SEARCH_LIMIT", "12"))
    data = _request("GET", _EP_PROPERTIES, query=q)
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inesperada en búsqueda de propiedades")
    props, count, total = _parse_property_search_list(data)
    summaries = [_listing_summary(p) for p in props]
    return {"properties": summaries, "count": count, "total": total}
def _property_search_by_id(candidate: str) -> dict[str, Any]:
    data = _request("GET", _EP_PROP_SEARCH, query={"id": candidate})
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inesperada en detalle de propiedad")
    return data
def property_details(body: dict[str, Any]) -> dict[str, Any]:
    ref = str(body.get("ref") or "").strip()
    if not ref:
        raise RuntimeError("Falta ref")
    data = _property_search_by_id(ref)
    prop_raw = data.get("data", data)
    if not isinstance(prop_raw, dict):
        raise RuntimeError("Propiedad no encontrada o respuesta inválida")
    prop_raw = _enrich_listing(prop_raw)
    ext = prop_raw.get("externalId") or (
        (prop_raw.get("source") or {}).get("externalId") if isinstance(prop_raw.get("source"), dict) else None
    )
    prop = {
        "id": prop_raw.get("id"),
        "externalId": ext,
        "ref": prop_raw.get("ref") or ref,
        "url": prop_raw.get("url"),
        "title": prop_raw.get("title"),
        "price": prop_raw.get("price"),
        "propertyType": prop_raw.get("propertyType"),
        "operation": prop_raw.get("operation"),
        "description": prop_raw.get("description"),
        "images": prop_raw.get("images", []),
        "city": prop_raw.get("city"),
        "province": prop_raw.get("province"),
        "zone": prop_raw.get("zone"),
        "bedrooms": prop_raw.get("bedrooms"),
        "bathrooms": prop_raw.get("bathrooms"),
        "surface": prop_raw.get("surface"),
    }
    if not prop.get("url") and prop.get("ref"):
        prop["url"] = f"{_PUBLIC_BASE}/propiedades/{prop['ref']}"
    has_agent = False
    agent_info = None
    if prop_raw.get("isManagedByIagestion"):
        ag = prop_raw.get("agent") or {}
        aid = prop_raw.get("agentId")
        name = f"{ag.get('nombre') or ''} {ag.get('apellidos') or ''}".strip()
        if aid and name:
            has_agent = True
            agent_info = {
                "id": str(aid),
                "name": name,
                "phone": ag.get("movil") or ag.get("telefono"),
                "email": ag.get("email"),
            }
    return {"property": prop, "has_agent": has_agent, "agent_info": agent_info}
def property_interest(body: dict[str, Any]) -> dict[str, Any]:
    ext = body.get("external_id")
    candidates = [str(x) for x in (ext, body.get("ref")) if x]
    if not candidates:
        raise RuntimeError("Falta external_id o ref para property_interest")
    last_err: str | None = None
    for cid in candidates:
        try:
            data = _property_search_by_id(cid)
            prop_raw = data.get("data", data)
            if isinstance(prop_raw, dict) and prop_raw.get("title"):
                idx = body.get("property_index")
                parsed = {
                    "property": {},
                    "has_agent": False,
                    "agent_info": None,
                    "property_index": idx,
                }
                full = property_details({"ref": str(prop_raw.get("ref") or cid)})
                parsed["property"] = {
                    **full["property"],
                    "externalId": full["property"].get("externalId"),
                }
                parsed["has_agent"] = full["has_agent"]
                parsed["agent_info"] = full["agent_info"]
                return parsed
        except RuntimeError as e:
            last_err = str(e)
            continue
    raise RuntimeError(last_err or "No se pudo resolver la propiedad")
def search_contact(body: dict[str, Any]) -> dict[str, Any]:
    tel = str(body.get("telefono") or "").strip()
    if not tel:
        raise RuntimeError("telefono es obligatorio")
    try:
        data = _request("GET", _EP_CONTACT_SEARCH, query={"telefono": tel})
    except RuntimeError as e:
        if str(e).startswith("SaaS HTTP 404"):
            return {"contactos": [], "total": 0, "message": "No se encontraron contactos con ese teléfono"}
        raise
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inválida en búsqueda de contacto")
    inner = data.get("data", data)
    contactos = inner.get("contactos", []) if isinstance(inner, dict) else []
    if not isinstance(contactos, list):
        contactos = []
    return {"contactos": contactos, "total": len(contactos), "message": inner.get("message", "ok")}
def create_contact(body: dict[str, Any]) -> dict[str, Any]:
    nombre = body.get("nombre")
    if not nombre:
        raise RuntimeError("nombre es obligatorio")
    if not body.get("telefono") and not body.get("email"):
        raise RuntimeError("Se requiere telefono o email")
    payload: dict[str, Any] = {"nombre": nombre}
    if body.get("telefono"):
        payload["telefono"] = body["telefono"]
    if body.get("email"):
        payload["email"] = body["email"]
    if body.get("apellidos"):
        payload["apellidos"] = body["apellidos"]
    if body.get("idAgente"):
        payload["idAgente"] = body["idAgente"]
    if body.get("observaciones"):
        payload["observaciones"] = body["observaciones"]
    data = _request("POST", _EP_CONTACT_CREATE, json_body=payload)
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inválida al crear contacto")
    cid = _find_id(data, ("id_contacto", "id_usuario", "idContacto"))
    inner = data.get("data") if isinstance(data.get("data"), dict) else {}
    msg = (
        inner.get("message")
        or inner.get("mensaje")
        or data.get("message")
        or "Contacto creado"
    )
    return {"id_contacto": cid, "id_usuario": cid, "message": str(msg)}
def create_demand(body: dict[str, Any]) -> dict[str, Any]:
    id_inm = body.get("id_inmueble")
    id_ct = body.get("id_contacto")
    if not id_inm:
        raise RuntimeError("id_inmueble es obligatorio")
    if not id_ct:
        raise RuntimeError("id_contacto es obligatorio (usa search_contact o create_contact antes)")
    payload: dict[str, Any] = {"id_inmueble": str(id_inm), "id_contacto": str(id_ct)}
    if body.get("telefono"):
        payload["telefono"] = str(body["telefono"])
    if body.get("nombre"):
        payload["nombre"] = body["nombre"]
    if body.get("email"):
        payload["email"] = body["email"]
    if body.get("alias"):
        payload["alias"] = body["alias"]
    if body.get("observaciones"):
        payload["observaciones"] = body["observaciones"]
    data = _request("POST", _EP_DEMANDS, json_body=payload)
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inválida al crear demanda")
    inner = data.get("data", data)
    id_demanda = _find_id(inner, ("id_demanda", "idDemanda", "demand_id"))
    id_usuario = _find_id(inner, ("id_usuario", "idUsuario"))
    return {
        "id_demanda": id_demanda,
        "id_usuario": id_usuario,
        "message": (inner.get("message") if isinstance(inner, dict) else None)
        or data.get("message")
        or "Demanda creada",
        "raw_response": inner,
    }
def _gestiones_for_agent_day(agent_id: str, date_yyyy_mm_dd: str) -> list[dict[str, Any]]:
    data = _request("GET", _EP_GESTIONES, query={"agentId": agent_id})
    if not isinstance(data, dict):
        return []
    rows = data.get("data", [])
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for g in rows:
        if not isinstance(g, dict):
            continue
        fp = str(g.get("FechaPlanificada") or g.get("fechaPlanificada") or "")
        est = str(g.get("Estado") or g.get("estado") or "")
        if fp.startswith(date_yyyy_mm_dd) and est == "Planificada":
            out.append(g)
    return out
def _busy_hhmm(gestiones: list[dict[str, Any]]) -> list[str]:
    busy: list[str] = []
    for g in gestiones:
        hp = g.get("HoraPlanificada") or g.get("horaPlanificada")
        fp = g.get("FechaPlanificada") or g.get("fechaPlanificada") or ""
        if hp:
            m = re.match(r"(\d{1,2}:\d{2})", str(hp))
            if m:
                busy.append(m.group(1))
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})", str(fp))
        if m:
            busy.append(m.group(2))
    return busy
def check_agent_availability(body: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(body.get("agent_id") or "").strip()
    date = str(body.get("date") or "").strip()
    if not agent_id or not date:
        raise RuntimeError("agent_id y date (YYYY-MM-DD) son obligatorios")
    gestiones = _gestiones_for_agent_day(agent_id, date)
    busy_times = _busy_hhmm(gestiones)
    start_h = int(os.environ.get("KISS_SAAS_WORK_START_HOUR", "8"))
    end_h = int(os.environ.get("KISS_SAAS_WORK_END_HOUR", "17"))
    all_slots = [f"{h:02d}:00" for h in range(start_h, end_h)]
    avail = [s for s in all_slots if s not in busy_times]
    busy_slots = [{"time": t, "type": "visita"} for t in busy_times]
    return {
        "agent_id": agent_id,
        "date": date,
        "available_slots": avail,
        "busy_slots": busy_slots,
        "total_slots": len(avail),
    }
def schedule_visit(body: dict[str, Any]) -> dict[str, Any]:
    pid = str(body.get("property_external_id") or "").strip()
    aid = str(body.get("agent_id") or "").strip()
    date = str(body.get("date") or "").strip()
    time_s = str(body.get("time") or "").strip()
    time_out = time_s
    if not all([pid, aid, date, time_s]):
        raise RuntimeError("Faltan property_external_id, agent_id, date o time")
    id_demanda = body.get("id_demanda")
    if not id_demanda:
        raise RuntimeError(
            "id_demanda es obligatorio para agendar (crea la demanda con create_demand antes)"
        )
    time_api = time_s if len(time_s.split(":")) == 3 else f"{time_s}:00"
    fecha_planificada = f"{date} {time_api}"
    payload: dict[str, Any] = {
        "id_inmueble": pid,
        "IdComercial": aid,
        "Tipo": "visita",
        "Titulo": body.get("title") or f"Visita programada - {pid}",
        "Descripcion": body.get("description") or f"Visita propiedad {pid}",
        "fechaPlanificada": fecha_planificada,
        "Estado": "Planificada",
        "id_demanda": str(id_demanda),
    }
    if body.get("id_contacto"):
        payload["id_contacto"] = str(body["id_contacto"])
    if body.get("user_name"):
        payload["nombre"] = str(body["user_name"])
    if body.get("user_phone"):
        payload["telefono"] = str(body["user_phone"])
    data = _request("POST", _EP_GESTION_CREATE, json_body=payload)
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inválida al crear gestión")
    inner = data.get("data", {})
    gid = None
    if isinstance(inner, dict):
        gid = inner.get("id_gestion") or inner.get("idgestion")
    if not gid:
        gid = _find_id(data, ("id_gestion", "idgestion", "IdGestion"))
    return {
        "gestion_id": str(gid) if gid else "",
        "property_id": pid,
        "agent_id": aid,
        "date": date,
        "time": time_out[:5] if len(time_out) >= 5 and time_out[2] == ":" else time_out,
        "status": "confirmed",
        "message": (inner.get("message") if isinstance(inner, dict) else None)
        or data.get("message")
        or "Visita agendada",
    }
def cancel_visit(body: dict[str, Any]) -> dict[str, Any]:
    gid = str(body.get("gestion_id") or "").strip()
    if not gid:
        raise RuntimeError("gestion_id es obligatorio")
    _request("POST", _EP_GESTION_DELETE, json_body={"Id_Gestion": gid})
    return {"gestion_id": gid, "status": "cancelled", "message": "Visita cancelada"}


TOOLS: dict[str, Any] = {
    "search_properties": search_properties,
    "property_details": property_details,
    "property_interest": property_interest,
    "search_contact": search_contact,
    "create_contact": create_contact,
    "create_demand": create_demand,
    "check_agent_availability": check_agent_availability,
    "schedule_visit": schedule_visit,
    "cancel_visit": cancel_visit,
}
