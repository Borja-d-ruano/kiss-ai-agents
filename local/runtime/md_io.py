from __future__ import annotations
import json
from pathlib import Path
AGENT_FILES = ("agent.md", "prompt.md", "tools.md", "data.md", "done.md", "memory.md", "steps.md", "schedule.md")
def _skip_input_path(folder: Path, f: Path) -> bool:
    try:
        rel = f.relative_to(folder)
    except ValueError:
        return True
    ps = rel.parts
    return len(ps) >= 2 and ps[0] == "input" and ps[1] == "session"
def load_agent(folder: Path, *, include_output: bool = True) -> str:
    folder = Path(folder)
    parts: list[str] = []
    for name in AGENT_FILES:
        p = folder / name
        if p.exists() and (t := p.read_text(encoding="utf-8").strip()):
            parts.append(f"# {name}\n\n{t}")
    subs = ("input", "output") if include_output else ("input",)
    for sub in subs:
        d = folder / sub
        if d.exists():
            for f in sorted(d.rglob("*")):
                if not f.is_file() or _skip_input_path(folder, f):
                    continue
                if f.suffix in (".md", ".txt", ".json", ".csv", ".py"):
                    parts.append(f"# {f.relative_to(folder)}\n\n{f.read_text(encoding='utf-8')}")
    return "\n\n---\n\n".join(parts)
def sanitize_session_id(s: str) -> str:
    s = (s or "").strip() or "default"
    out = [c if c.isalnum() or c in "._-" else "_" for c in s[:128]]
    return "".join(out).strip("._") or "default"
def session_messages_path(folder: Path, session_id: str) -> Path:
    folder = Path(folder)
    d = folder / "input" / "session"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{sanitize_session_id(session_id)}.jsonl"
def read_session_messages(folder: Path, session_id: str) -> list[dict]:
    p = session_messages_path(folder, session_id)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict) and o.get("role") in ("user", "assistant") and isinstance(o.get("content"), str):
            out.append({"role": o["role"], "content": o["content"]})
    return out
def write_session_messages(folder: Path, session_id: str, messages: list[dict]) -> None:
    p = session_messages_path(folder, session_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps({"role": m["role"], "content": m["content"]}, ensure_ascii=False) + "\n"
        for m in messages
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
    ]
    p.write_text("".join(lines), encoding="utf-8")
def apply_writes(folder: Path, writes: list) -> None:
    folder = Path(folder)
    for w in writes:
        path = folder / w["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(w.get("content", ""), encoding="utf-8")
def _json_block(raw: str) -> str:
    s, e = raw.find("```json"), -1
    if s >= 0:
        e = raw.find("```", s + 7)
    return raw[s + 7 : e].strip() if s >= 0 and e > s else ""
def _clean_lists(o: dict) -> dict:
    out = dict(o)
    for k in ("openai_mcp_tools", "anthropic_mcp_servers"):
        if k not in out or not isinstance(out.get(k), list):
            out[k] = []
            continue
        cl = []
        for it in out[k]:
            if not isinstance(it, dict):
                continue
            t = str(it.get("type", "")).strip()
            n = str(it.get("name", "")).strip()
            u = str(it.get("url", it.get("server_url", ""))).strip()
            if t and (n or u):
                cl.append(it)
        out[k] = cl
    return out
def _expand_neutral(o: dict) -> dict:
    out = _clean_lists(o)
    neutral = out.get("mcp_servers")
    if not isinstance(neutral, list):
        return out
    oa, ant = list(out["openai_mcp_tools"]), list(out["anthropic_mcp_servers"])
    for e in neutral:
        if not isinstance(e, dict):
            continue
        name = str(e.get("name", "")).strip()
        url = str(e.get("url", "")).strip()
        typ = str(e.get("type", "mcp")).strip() or "mcp"
        if not name:
            continue
        if url:
            oa.append({"type": typ, "name": name, "url": url})
        ant.append({"type": typ, "name": name, **({"url": url} if url else {})})
    out["openai_mcp_tools"] = oa
    out["anthropic_mcp_servers"] = ant
    return out
def _try_dict_from_json_text(text: str) -> dict | None:
    try:
        o = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(o, dict):
        return None
    return _expand_neutral(o)
def resolve_tools_config(agent_dir: Path | str | None, normalizer=None) -> dict:
    """Una pasada: parse + neutral mcp_servers → listas por proveedor; si falla, 1× normalizer o error en output/."""
    if not agent_dir:
        return {}
    folder = Path(agent_dir)
    p = folder / "tools.md"
    if not p.exists():
        return {}
    raw = p.read_text(encoding="utf-8")
    cand = _json_block(raw)
    if not cand.strip():
        return {}
    r = _try_dict_from_json_text(cand)
    if r is not None:
        return r
    if callable(normalizer):
        try:
            fx = normalizer(raw)
            if isinstance(fx, str) and fx.strip():
                r2 = _try_dict_from_json_text(fx.strip())
                if r2 is not None:
                    return r2
        except Exception:
            pass
    outd = folder / "output"
    outd.mkdir(parents=True, exist_ok=True)
    (outd / "tools-md-invalid.md").write_text("# tools.md inválido\n\nEl bloque ```json no es JSON válido o no pasó validación tras normalizar.\n", encoding="utf-8")
    return {}
def parse_or_normalize_tools_md(agent_dir: Path | str | None, normalizer=None) -> dict:
    """Compat: equivale a resolve_tools_config (misma semántica, error en output si falla)."""
    return resolve_tools_config(agent_dir, normalizer)
