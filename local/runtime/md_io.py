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
LIST_MERGE_KEYS = ("mcp_servers", "openai_mcp_tools", "anthropic_mcp_servers")
MAX_TOOLS_INCLUDE_DEPTH = 5
def _tools_include_paths(o: dict) -> list[str]:
    inc = o.get("include", o.get("includes"))
    if isinstance(inc, str) and inc.strip():
        return [inc.strip()]
    if isinstance(inc, list):
        return [str(x).strip() for x in inc if str(x).strip()]
    return []
def _safe_tools_json_path(folder: Path, rel: str) -> Path | None:
    folder = folder.resolve()
    if rel.startswith(("/", "\\")):
        return None
    if ".." in Path(rel).parts:
        return None
    cand = (folder / rel).resolve()
    try:
        cand.relative_to(folder)
    except ValueError:
        return None
    if cand.suffix.lower() != ".json" or not cand.is_file():
        return None
    return cand
def _empty_merge_lists() -> dict[str, list]:
    return {k: [] for k in LIST_MERGE_KEYS}
def _merge_list_fields(acc: dict[str, list], src: dict) -> None:
    for k in LIST_MERGE_KEYS:
        v = src.get(k)
        if isinstance(v, list):
            acc.setdefault(k, [])
            acc[k].extend(v)
def _mcp_dedupe_key(it: dict) -> tuple[str, str] | None:
    n = str(it.get("name", "")).strip().lower()
    u = str(it.get("url", it.get("server_url", ""))).strip().lower()
    if not n and not u:
        return None
    return (n, u)
def _dedupe_mcp_lists(d: dict) -> dict:
    out = dict(d)
    for k in LIST_MERGE_KEYS:
        lst = out.get(k)
        if not isinstance(lst, list):
            continue
        seen: set[tuple[str, str]] = set()
        nl: list = []
        for it in lst:
            if not isinstance(it, dict):
                continue
            dk = _mcp_dedupe_key(it)
            if dk is None or dk not in seen:
                if dk is not None:
                    seen.add(dk)
                nl.append(it)
        out[k] = nl
    return out
def _trim_anthropic_skills(o: dict) -> dict:
    out = dict(o)
    sk = out.get("anthropic_skills")
    if not isinstance(sk, list):
        out.pop("anthropic_skills", None)
        return out
    good: list[dict] = []
    for it in sk:
        if len(good) >= 8:
            break
        if not isinstance(it, dict):
            continue
        t = str(it.get("type", "")).strip()
        sid = str(it.get("skill_id", "")).strip()
        if not t or not sid:
            continue
        entry: dict[str, str] = {"type": t, "skill_id": sid}
        ver = it.get("version")
        vs = str(ver).strip() if ver is not None else ""
        if vs:
            entry["version"] = vs
        good.append(entry)
    out["anthropic_skills"] = good
    return out
def _finalize_tools_dict(d: dict) -> dict:
    return _trim_anthropic_skills(_dedupe_mcp_lists(d))
def _tools_merge_object_lists(folder: Path, o: dict, depth: int, visiting: set[Path]) -> dict[str, list]:
    acc = _empty_merge_lists()
    for rel in _tools_include_paths(o):
        child = _safe_tools_json_path(folder, rel)
        if child is None:
            continue
        sub = _tools_merge_json_file(folder, child, depth + 1, visiting)
        _merge_list_fields(acc, sub)
    local = {k: v for k, v in o.items() if k not in ("include", "includes")}
    loc_exp = _expand_neutral(_clean_lists(local))
    _merge_list_fields(acc, {k: loc_exp.get(k, []) for k in LIST_MERGE_KEYS})
    return acc
def _tools_merge_json_file(folder: Path, path: Path, depth: int, visiting: set[Path]) -> dict[str, list]:
    path = path.resolve()
    if depth > MAX_TOOLS_INCLUDE_DEPTH or path in visiting:
        return _empty_merge_lists()
    visiting.add(path)
    try:
        try:
            raw = path.read_text(encoding="utf-8")
            o = json.loads(raw)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return _empty_merge_lists()
        if not isinstance(o, dict):
            return _empty_merge_lists()
        return _tools_merge_object_lists(folder, o, depth, visiting)
    finally:
        visiting.discard(path)
def _tools_resolve_includes(folder: Path, o: dict) -> dict:
    visiting: set[Path] = set()
    lists_acc = _tools_merge_object_lists(folder, o, 0, visiting)
    local = {k: v for k, v in o.items() if k not in ("include", "includes")}
    loc_exp = _expand_neutral(_clean_lists(local))
    out = {k: v for k, v in loc_exp.items() if k not in LIST_MERGE_KEYS}
    for k in LIST_MERGE_KEYS:
        out[k] = lists_acc[k]
    return out
def resolve_tools_config(agent_dir: Path | str | None, normalizer=None) -> dict:
    """Parse tools.md JSON, optional include/includes → .json bajo el agente, merge MCP lists, dedupe, anthropic_skills ≤8."""
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
    try:
        o = json.loads(cand)
    except json.JSONDecodeError:
        o = None
    if isinstance(o, dict):
        return _finalize_tools_dict(_tools_resolve_includes(folder, o))
    if callable(normalizer):
        try:
            fx = normalizer(raw)
            if isinstance(fx, str) and fx.strip():
                try:
                    o2 = json.loads(fx.strip())
                except json.JSONDecodeError:
                    o2 = None
                if isinstance(o2, dict):
                    return _finalize_tools_dict(_tools_resolve_includes(folder, o2))
        except Exception:
            pass
    outd = folder / "output"
    outd.mkdir(parents=True, exist_ok=True)
    (outd / "tools-md-invalid.md").write_text("# tools.md inválido\n\nEl bloque ```json no es JSON válido o no pasó validación tras normalizar.\n", encoding="utf-8")
    return {}
def parse_or_normalize_tools_md(agent_dir: Path | str | None, normalizer=None) -> dict:
    """Compat: equivale a resolve_tools_config (misma semántica, error en output si falla)."""
    return resolve_tools_config(agent_dir, normalizer)
