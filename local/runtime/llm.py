"""OpenAI Responses + Anthropic Messages (urllib); normalización tools compartida por nombre."""
from __future__ import annotations
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
_KISS_WRITE_RE = re.compile(r"^```kiss-write\s+path=(\S+)\s*\r?\n(.*?)^```\s*", re.MULTILINE | re.DOTALL)
_KISS_FILE_HINT = (
    "Para persistir archivos en la carpeta del agente (memory.md, output/*.md, etc.), "
    "añade bloques exactamente así (repite si hay varios ficheros); el runtime los escribe con `apply_writes`:\n"
    "```kiss-write path=memory.md\ncontenido completo del fichero\n```"
)
def _kiss_path_ok(p: str) -> bool:
    p = p.strip()
    return bool(p) and ".." not in p and not p.startswith(("/", "\\"))
def _kiss_writes_from_text(text: str) -> list[dict]:
    by: dict[str, str] = {}
    for m in _KISS_WRITE_RE.finditer(text or ""):
        path, content = m.group(1).strip(), m.group(2).rstrip("\r\n")
        if _kiss_path_ok(path):
            by[path] = content
    return [{"path": k, "content": v} for k, v in by.items()]
def _strip_kiss_write_blocks(text: str) -> str:
    return _KISS_WRITE_RE.sub("", text or "").strip()
def _kiss_writes_bundle(raw: str, last_slug: str) -> tuple[list[dict], str]:
    raw = raw or ""
    clean = _strip_kiss_write_blocks(raw) or raw.strip()
    extras = _kiss_writes_from_text(raw)
    last_path = f"output/{last_slug}-last.md"
    writes: list[dict] = [{"path": last_path, "content": clean or raw}]
    seen = {last_path}
    for w in extras:
        p = w["path"]
        if p in seen or not _kiss_path_ok(p):
            continue
        writes.append({"path": p, "content": w["content"]})
        seen.add(p)
    return writes, clean or raw
def _post(url: str, data: dict, headers: dict[str, str], who: str = "") -> dict:
    r = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        p = f"{who} " if who else ""
        raise RuntimeError(f"{p}HTTP {e.code}: {e.read().decode(errors='replace')}") from e
def _oai_hdr() -> dict[str, str]:
    k = os.environ.get("OPENAI_API_KEY", "").strip()
    if not k:
        raise RuntimeError("Falta OPENAI_API_KEY")
    return {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
def _ant_hdr(beta: str) -> dict[str, str]:
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not k:
        raise RuntimeError("Falta ANTHROPIC_API_KEY")
    h = {"x-api-key": k, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    if beta.strip():
        h["anthropic-beta"] = beta.strip()
    return h
def _walk(o: Any, acc: list[str]) -> None:
    if isinstance(o, dict):
        if o.get("type") in ("output_text", "text") and "text" in o:
            acc.append(str(o["text"]))
        for v in o.values():
            _walk(v, acc)
    elif isinstance(o, list):
        for x in o:
            _walk(x, acc)
def _oai_txt(resp: dict) -> str:
    t = resp.get("output_text")
    if isinstance(t, str) and t.strip():
        return t.strip()
    a: list[str] = []
    _walk(resp.get("output", []), a)
    return "\n".join(a).strip()
def normalize_tools_openai(raw: str) -> str:
    m = os.environ.get("OPENAI_MODEL", "gpt-5.4").strip()
    sc = 'Corrige tools.md → SOLO JSON {"openai_mcp_tools":[],"anthropic_mcp_servers":[],"mcp_servers":[]} ' "sin markdown; arrays vacíos si falta data."
    return _oai_txt(_post("https://api.openai.com/v1/responses", {"model": m, "input": [{"role": "system", "content": sc}, {"role": "user", "content": raw[:12000]}]}, _oai_hdr(), "OpenAI"))
def normalize_tools_anthropic(raw: str) -> str:
    m = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip()
    uc = 'SOLO JSON {"openai_mcp_tools":[],"anthropic_mcp_servers":[],"mcp_servers":[]} ' "sin markdown.\n\n" + raw[:12000]
    r = _post("https://api.anthropic.com/v1/messages", {"model": m, "max_tokens": 2048, "messages": [{"role": "user", "content": uc}]}, _ant_hdr(""), "Anthropic")
    return "\n".join(str(b.get("text", "")) for b in r.get("content") or [] if b.get("type") == "text").strip()
def _oai_approve(resp: dict) -> list[dict]:
    if os.environ.get("KISS_OPENAI_MCP_AUTO_APPROVE", "1") in ("0", "false", "no"):
        return []
    out: list[dict] = []
    def sc(o: Any) -> None:
        if isinstance(o, dict):
            t = str(o.get("type", ""))
            if "mcp_approval" in t or t.endswith("_approval_request"):
                aid = o.get("approval_request_id") or o.get("id")
                if aid:
                    out.append({"type": "mcp_approval_response", "approve": True, "approval_request_id": aid})
            for v in o.values():
                sc(v)
        elif isinstance(o, list):
            for x in o:
                sc(x)
    sc(resp)
    return out
def _oai_local_shell_enabled() -> bool:
    if os.environ.get("KISS_OPENAI_DISABLE_SHELL") in ("1", "true", "yes"):
        return False
    return (os.environ.get("KISS_OPENAI_SHELL_MODE") or "hosted").strip().lower() == "local"
def _oai_shell_tool_entry() -> dict | None:
    if os.environ.get("KISS_OPENAI_DISABLE_SHELL") in ("1", "true", "yes"):
        return None
    mode = (os.environ.get("KISS_OPENAI_SHELL_MODE") or "hosted").strip().lower()
    if mode in ("off", "none", "false", "0"):
        return None
    if mode == "local":
        return {"type": "shell"}
    return {"type": "shell", "environment": {"type": "container_auto"}}
def _oai_walk_shell_calls(o: Any, acc: list[dict]) -> None:
    if isinstance(o, dict):
        if o.get("type") == "shell_call":
            acc.append(o)
        for v in o.values():
            _oai_walk_shell_calls(v, acc)
    elif isinstance(o, list):
        for x in o:
            _oai_walk_shell_calls(x, acc)
def _oai_run_shell_call(call: dict, agent_dir: Path | None, default_timeout: int) -> dict:
    """shell_call_output para Responses (local); output = lista {stdout, stderr, outcome} alineado con openai-python."""
    call_id = call.get("call_id") or call.get("id")
    action = call.get("action") if isinstance(call.get("action"), dict) else {}
    commands = action.get("commands")
    mol = action.get("max_output_length")
    if not isinstance(mol, int) or mol <= 0:
        mol = call.get("max_output_length")
    if not isinstance(mol, int) or mol <= 0:
        mol = None
    timeout_sec = default_timeout
    tms = action.get("timeout_ms")
    if tms is not None:
        try:
            timeout_sec = max(1, int(tms) // 1000)
        except (TypeError, ValueError):
            pass
    cwd = action.get("working_directory") or os.environ.get("KISS_BASH_CWD")
    if not cwd and agent_dir:
        cwd = str(agent_dir.resolve())
    if not cwd:
        cwd = os.getcwd()
    raw_env = action.get("env")
    full_env = dict(os.environ)
    if isinstance(raw_env, dict):
        for k, v in raw_env.items():
            full_env[str(k)] = str(v)
    def _truncate(so: str, se: str) -> tuple[str, str]:
        if not mol:
            return so, se
        cap = mol
        if len(so) + len(se) <= cap:
            return so, se
        if len(so) >= cap:
            return so[:cap] + "\n…(truncado, max_output_length)", ""
        rest = cap - len(so)
        return so, (se[:rest] + "\n…(truncado, max_output_length)" if se else "")
    chunks: list[dict[str, Any]] = []
    if isinstance(commands, list) and commands:
        for cmd in commands:
            scmd = cmd if isinstance(cmd, str) else json.dumps(cmd)
            try:
                p = subprocess.run(scmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout_sec, env=full_env)
                so, se = _truncate(p.stdout or "", p.stderr or "")
                rc = 0 if p.returncode in (0, None) else int(p.returncode)
                chunks.append({"stdout": so, "stderr": se, "outcome": {"type": "exit", "exit_code": rc}})
            except subprocess.TimeoutExpired:
                so, se = _truncate("", f"Error: timeout tras {timeout_sec}s")
                chunks.append({"stdout": so, "stderr": se, "outcome": {"type": "timeout"}})
                break
    else:
        so, se = _truncate("", "(KISS) shell_call sin `action.commands` reconocible.")
        chunks.append({"stdout": so, "stderr": se, "outcome": {"type": "exit", "exit_code": 1}})

    out: dict[str, Any] = {"type": "shell_call_output", "output": chunks, "status": "completed"}
    if call_id:
        out["call_id"] = str(call_id)
    if mol is not None:
        out["max_output_length"] = mol
    return out
def _oai_shell_followups(resp: dict, agent_dir: Path | None) -> list[dict] | None:
    if not _oai_local_shell_enabled():
        return None
    calls: list[dict] = []
    _oai_walk_shell_calls(resp.get("output"), calls)
    if not calls:
        return None
    to = int(os.environ.get("KISS_BASH_TIMEOUT", "120"))
    return [_oai_run_shell_call(c, agent_dir, to) for c in calls]
def _normalize_openai_mcp_tools(entries: list) -> list[dict]:
    """OpenAI Responses Remote MCP requiere server_label + server_url (no solo name/url de tools.md)."""
    out: list[dict] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        if str(e.get("type", "mcp")).lower() != "mcp":
            out.append(e)
            continue
        label = e.get("server_label") or e.get("name")
        surl = e.get("server_url") or e.get("url")
        if not label or not surl:
            out.append(e)
            continue
        norm: dict = {"type": "mcp", "server_label": str(label).strip(), "server_url": str(surl).strip()}
        for k in ("authorization", "allowed_tools", "require_approval"):
            if k in e:
                norm[k] = e[k]
        out.append(norm)
    return out
def _oai_tools(cfg: dict) -> list[dict]:
    o: list[dict] = []
    sh = _oai_shell_tool_entry()
    if sh:
        o.append(sh)
    if os.environ.get("KISS_OPENAI_ENABLE_CODE_INTERPRETER") in ("1", "true", "yes"):
        o.append({"type": "code_interpreter", "container": {"type": "auto", "memory_limit": os.environ.get("KISS_OPENAI_CI_MEMORY", "4g")}})
    o.extend(_normalize_openai_mcp_tools(cfg.get("openai_mcp_tools") or []))
    return o
def call_openai(*, prompt: str, context: str, agent_dir: Path | None = None, tools_cfg: dict | None = None) -> dict:
    m = os.environ.get("OPENAI_MODEL", "gpt-5.4").strip()
    cfg = tools_cfg if isinstance(tools_cfg, dict) else {}
    tools = _oai_tools(cfg)
    base_sys = os.environ.get("KISS_OPENAI_INSTRUCTIONS", "Eres KISS Agents; usa tools si hace falta; el host guarda salida en output/.").strip()
    sys = f"{base_sys}\n\n{_KISS_FILE_HINT}"
    body = f"{context}\n\n---\n\nUSER_PROMPT:\n{prompt}"
    items: Any = [{"role": "system", "content": sys}, {"role": "user", "content": body}]
    ad = Path(agent_dir).resolve() if agent_dir else None
    prev, last = None, ""
    for _ in range(64):
        pl: dict = {"model": m, "input": items, "tools": tools}
        if os.environ.get("KISS_OPENAI_STORE_FALSE") in ("1", "true"):
            pl["store"] = False
        if prev:
            pl["previous_response_id"] = prev
        resp = _post("https://api.openai.com/v1/responses", pl, _oai_hdr(), "OpenAI")
        prev = resp.get("id") or prev
        last = _oai_txt(resp) or last
        ap = _oai_approve(resp)
        if ap:
            items = ap
            continue
        sh = _oai_shell_followups(resp, ad)
        if sh:
            items = sh
            continue
        st = str(resp.get("status", "completed"))
        if st in ("completed", "failed", "cancelled"):
            break
        break
    text = last or "(sin texto en output)"
    writes, display = _kiss_writes_bundle(text, "openai")
    return {"final": True, "message": display[:2000], "writes": writes}
def _bash(cmd: str, to: int, ad: Path | None) -> str:
    cwd = os.environ.get("KISS_BASH_CWD") or (str(ad) if ad else "") or os.getcwd()
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=to)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return f"Error: timeout tras {to}s"
def _ant_build(cfg: dict) -> tuple[list[dict], list[dict], str]:
    t, ms, b = [], [], []
    fl = os.environ.get("KISS_ANTHROPIC_TOOLS", "bash,code_execution,mcp").lower()
    if "bash" in fl:
        t.append({"type": "bash_20250124", "name": "bash"})
    if "code_execution" in fl:
        t.append({"type": "code_execution_20250825", "name": "code_execution"})
    if "mcp" in fl:
        ms = cfg.get("anthropic_mcp_servers") or []
    if ms:
        b.append("mcp-client-2025-11-20")
        for s in ms:
            n = s.get("name")
            if n:
                t.append({"type": "mcp_toolset", "mcp_server_name": n})
    ex = os.environ.get("KISS_ANTHROPIC_BETA_HEADERS", "").strip()
    if ex:
        b.extend(x.strip() for x in ex.split(",") if x.strip())
    return t, ms, ",".join(b)
def call_anthropic(*, prompt: str, context: str, agent_dir: Path | None = None, tools_cfg: dict | None = None) -> dict:
    m = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip()
    mt = int(os.environ.get("KISS_ANTHROPIC_MAX_TOKENS", "8192"))
    ad = Path(agent_dir).resolve() if agent_dir else None
    cfg = tools_cfg if isinstance(tools_cfg, dict) else {}
    tools, mcp, beta = _ant_build(cfg)
    ut = f"{context}\n\n---\n\nUSER_PROMPT:\n{prompt}"
    msgs: list[dict] = [{"role": "user", "content": ut}]
    to = int(os.environ.get("KISS_BASH_TIMEOUT", "120"))
    fin = ""
    for _ in range(48):
        pl: dict = {"model": m, "max_tokens": mt, "messages": msgs, "system": _KISS_FILE_HINT}
        if tools:
            pl["tools"] = tools
        if mcp:
            pl["mcp_servers"] = mcp
        resp = _post("https://api.anthropic.com/v1/messages", pl, _ant_hdr(beta), "Anthropic")
        content = resp.get("content") or []
        fin = "\n".join(str(b.get("text", "")) for b in content if b.get("type") == "text").strip() or fin
        st = resp.get("stop_reason", "")
        if st == "end_turn":
            break
        if st != "tool_use":
            break
        tr: list[dict] = []
        for bl in content:
            if bl.get("type") != "tool_use":
                continue
            tid, nm = bl.get("id"), bl.get("name", "")
            if nm == "bash":
                inp = bl.get("input") or {}
                out = "Bash session restart (stub local: no stateful shell)" if inp.get("restart") else _bash(str(inp.get("command", "")), to, ad)
                tr.append({"type": "tool_result", "tool_use_id": tid, "content": out})
            else:
                tr.append({"type": "tool_result", "tool_use_id": tid, "content": f"(KISS) `{nm}` no en cliente; code_execution/MCP server-side.", "is_error": True})
        if not tr:
            break
        msgs += [{"role": "assistant", "content": content}, {"role": "user", "content": tr}]
    text = fin or "(sin texto en output)"
    writes, display = _kiss_writes_bundle(text, "anthropic")
    return {"final": True, "message": display[:2000], "writes": writes}
