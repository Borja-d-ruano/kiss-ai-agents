"""OpenAI Responses + Anthropic Messages (urllib)."""
from __future__ import annotations
import json, os, re, subprocess, time, urllib.error, urllib.request
from pathlib import Path
from typing import Any
_KW = re.compile(r"^```kiss-write\s+path=(\S+)\s*\r?\n(.*?)^```\s*", re.MULTILINE | re.DOTALL)
_HINT = (
    "Persiste en la carpeta del agente con bloques `kiss-write` (el runtime llama a apply_writes):\n"
    "```kiss-write path=memory.md\ncontenido\n```"
)
def _ok(p: str) -> bool:
    p = p.strip()
    return bool(p) and ".." not in p and not p.startswith(("/", "\\"))
def _kw_extr(text: str) -> list[dict]:
    by: dict[str, str] = {}
    for m in _KW.finditer(text or ""):
        path, c = m.group(1).strip(), m.group(2).rstrip("\r\n")
        if _ok(path):
            by[path] = c
    return [{"path": k, "content": v} for k, v in by.items()]
def _kw_strip(t: str) -> str:
    return _KW.sub("", t or "").strip()
def _bundle(raw: str, slug: str) -> tuple[list[dict], str]:
    raw = raw or ""
    clean = _kw_strip(raw) or raw.strip()
    ex, lp = _kw_extr(raw), f"output/{slug}-last.md"
    w, seen = [{"path": lp, "content": clean or raw}], {lp}
    for x in ex:
        p = x["path"]
        if p not in seen and _ok(p):
            w.append(x)
            seen.add(p)
    return w, clean or raw
def _req(method: str, url: str, headers: dict[str, str], body: dict | None, who: str = "") -> dict:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        p = f"{who} " if who else ""
        raise RuntimeError(f"{p}HTTP {e.code}: {e.read().decode(errors='replace')}") from e
def _post(url: str, body: dict, headers: dict[str, str], who: str = "") -> dict:
    return _req("POST", url, headers, body, who)
def _get(url: str, headers: dict[str, str], who: str = "") -> dict:
    return _req("GET", url, headers, None, who)
def _oai_poll(r: dict, headers: dict[str, str]) -> dict:
    interval, mx = float(os.environ.get("KISS_OPENAI_POLL_INTERVAL", "1.5")), int(os.environ.get("KISS_OPENAI_POLL_MAX", "400"))
    for _ in range(mx):
        st = str(r.get("status", "completed"))
        if st not in ("queued", "in_progress"):
            return r
        rid = r.get("id")
        if not rid:
            return r
        time.sleep(interval)
        r = _get(f"https://api.openai.com/v1/responses/{rid}", headers, "OpenAI")
    return r
def _reply_cap() -> int:
    try:
        n = int(os.environ.get("KISS_REPLY_MAX_CHARS", "16000").strip())
    except ValueError:
        n = 16000
    return max(500, n)
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
def _walk_txt(o: Any, acc: list[str]) -> None:
    if isinstance(o, dict):
        if o.get("type") in ("output_text", "text") and "text" in o:
            acc.append(str(o["text"]))
        for v in o.values():
            _walk_txt(v, acc)
    elif isinstance(o, list):
        for x in o:
            _walk_txt(x, acc)
def _oai_txt(resp: dict) -> str:
    t = resp.get("output_text")
    if isinstance(t, str) and t.strip():
        return t.strip()
    a: list[str] = []
    _walk_txt(resp.get("output", []), a)
    return "\n".join(a).strip()
def normalize_tools_openai(raw: str) -> str:
    m = os.environ.get("OPENAI_MODEL", "gpt-5.4").strip()
    sc = 'Corrige tools.md → SOLO JSON {"openai_mcp_tools":[],"anthropic_mcp_servers":[],"mcp_servers":[]} sin markdown; arrays vacíos si falta data.'
    return _oai_txt(_post("https://api.openai.com/v1/responses", {"model": m, "input": [{"role": "system", "content": sc}, {"role": "user", "content": raw[:12000]}]}, _oai_hdr(), "OpenAI"))
def normalize_tools_anthropic(raw: str) -> str:
    m = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip()
    uc = 'SOLO JSON {"openai_mcp_tools":[],"anthropic_mcp_servers":[],"mcp_servers":[]} sin markdown.\n\n' + raw[:12000]
    r = _post("https://api.anthropic.com/v1/messages", {"model": m, "max_tokens": 2048, "messages": [{"role": "user", "content": uc}]}, _ant_hdr(""), "Anthropic")
    return "\n".join(str(b.get("text", "")) for b in r.get("content") or [] if b.get("type") == "text").strip()
def _oai_appr(resp: dict) -> list[dict]:
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
def _sh_local() -> bool:
    if os.environ.get("KISS_OPENAI_DISABLE_SHELL") in ("1", "true", "yes"):
        return False
    return (os.environ.get("KISS_OPENAI_SHELL_MODE") or "hosted").strip().lower() == "local"
def _sh_entry() -> dict | None:
    if os.environ.get("KISS_OPENAI_DISABLE_SHELL") in ("1", "true", "yes"):
        return None
    mode = (os.environ.get("KISS_OPENAI_SHELL_MODE") or "hosted").strip().lower()
    if mode in ("off", "none", "false", "0"):
        return None
    return {"type": "shell"} if mode == "local" else {"type": "shell", "environment": {"type": "container_auto"}}
def _sh_walk(o: Any, acc: list[dict]) -> None:
    if isinstance(o, dict):
        if o.get("type") == "shell_call":
            acc.append(o)
        for v in o.values():
            _sh_walk(v, acc)
    elif isinstance(o, list):
        for x in o:
            _sh_walk(x, acc)
def _sh_run(call: dict, agent_dir: Path | None, default_timeout: int) -> dict:
    cid = call.get("call_id") or call.get("id")
    act = call.get("action") if isinstance(call.get("action"), dict) else {}
    cmds, mol = act.get("commands"), act.get("max_output_length")
    if not isinstance(mol, int) or mol <= 0:
        mol = call.get("max_output_length")
    if not isinstance(mol, int) or mol <= 0:
        mol = None
    to = default_timeout
    if act.get("timeout_ms") is not None:
        try:
            to = max(1, int(act["timeout_ms"]) // 1000)
        except (TypeError, ValueError):
            pass
    cwd = act.get("working_directory") or os.environ.get("KISS_BASH_CWD") or (str(agent_dir.resolve()) if agent_dir else "") or os.getcwd()
    env = dict(os.environ)
    if isinstance(act.get("env"), dict):
        env.update({str(k): str(v) for k, v in act["env"].items()})
    def trunc(so: str, se: str) -> tuple[str, str]:
        if not mol or len(so) + len(se) <= mol:
            return so, se
        if len(so) >= mol:
            return so[:mol] + "\n…(truncado)", ""
        r = mol - len(so)
        return so, (se[:r] + "\n…(truncado)" if se else "")
    ch: list[dict[str, Any]] = []
    if isinstance(cmds, list) and cmds:
        for cmd in cmds:
            scmd = cmd if isinstance(cmd, str) else json.dumps(cmd)
            try:
                p = subprocess.run(scmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=to, env=env)
                so, se = trunc(p.stdout or "", p.stderr or "")
                rc = 0 if p.returncode in (0, None) else int(p.returncode)
                ch.append({"stdout": so, "stderr": se, "outcome": {"type": "exit", "exit_code": rc}})
            except subprocess.TimeoutExpired:
                so, se = trunc("", f"Error: timeout tras {to}s")
                ch.append({"stdout": so, "stderr": se, "outcome": {"type": "timeout"}})
                break
    else:
        so, se = trunc("", "(KISS) shell_call sin action.commands.")
        ch.append({"stdout": so, "stderr": se, "outcome": {"type": "exit", "exit_code": 1}})
    out: dict[str, Any] = {"type": "shell_call_output", "output": ch, "status": "completed"}
    if cid:
        out["call_id"] = str(cid)
    if mol is not None:
        out["max_output_length"] = mol
    return out
def _sh_fup(resp: dict, agent_dir: Path | None) -> list[dict] | None:
    if not _sh_local():
        return None
    calls: list[dict] = []
    _sh_walk(resp.get("output"), calls)
    if not calls:
        return None
    to = int(os.environ.get("KISS_BASH_TIMEOUT", "120"))
    return [_sh_run(c, agent_dir, to) for c in calls]
def _norm_mcp(entries: list) -> list[dict]:
    out: list[dict] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        if str(e.get("type", "mcp")).lower() != "mcp":
            out.append(e)
            continue
        lb, u = e.get("server_label") or e.get("name"), e.get("server_url") or e.get("url")
        if not lb or not u:
            out.append(e)
            continue
        d: dict = {"type": "mcp", "server_label": str(lb).strip(), "server_url": str(u).strip()}
        for k in ("authorization", "allowed_tools", "require_approval"):
            if k in e:
                d[k] = e[k]
        out.append(d)
    return out
def _oai_tools(cfg: dict) -> list[dict]:
    o: list[dict] = []
    e = _sh_entry()
    if e:
        o.append(e)
    if os.environ.get("KISS_OPENAI_ENABLE_CODE_INTERPRETER") in ("1", "true", "yes"):
        o.append({"type": "code_interpreter", "container": {"type": "auto", "memory_limit": os.environ.get("KISS_OPENAI_CI_MEMORY", "4g")}})
    o.extend(_norm_mcp(cfg.get("openai_mcp_tools") or []))
    return o
_PEND, _CT = frozenset({"in_progress", "calling", "incomplete"}), frozenset(
    {"mcp_call", "function_call", "custom_tool_call", "code_interpreter_call", "shell_call"}
)
def _pend_out(o: Any) -> bool:
    if isinstance(o, dict):
        return (str(o.get("type", "")) in _CT and str(o.get("status", "completed")) in _PEND) or any(_pend_out(v) for v in o.values())
    return isinstance(o, list) and any(_pend_out(x) for x in o)
def call_openai(
    *, prompt: str | None = None, context: str, messages: list[dict] | None = None, agent_dir: Path | None = None, tools_cfg: dict | None = None,
) -> dict:
    m = os.environ.get("OPENAI_MODEL", "gpt-5.4").strip()
    cfg = tools_cfg if isinstance(tools_cfg, dict) else {}
    tools = _oai_tools(cfg)
    bs = os.environ.get("KISS_OPENAI_INSTRUCTIONS", "Eres KISS Agents; usa tools si hace falta; el host guarda salida en output/.").strip()
    if messages is not None:
        sys = f"{bs}\n\n{_HINT}\n\n---\n\n# Carpeta del agente\n\n{context}"
        items: Any = [{"role": "system", "content": sys}] + [{"role": r, "content": c} for msg in messages if isinstance(msg, dict) and (r := msg.get("role")) in ("user", "assistant") and isinstance(c := msg.get("content"), str)]
    else:
        sys = f"{bs}\n\n{_HINT}"
        items = [{"role": "system", "content": sys}, {"role": "user", "content": f"{context}\n\n---\n\nUSER_PROMPT:\n{prompt}"}]
    ad = Path(agent_dir).resolve() if agent_dir else None
    prev, last = None, ""
    try:
        mot = max(256, int(os.environ.get("KISS_OPENAI_MAX_OUTPUT_TOKENS", "32768")))
    except ValueError:
        mot = 32768
    lim: dict[str, Any] = {"max_output_tokens": mot}
    try:
        n = int(os.environ.get("KISS_OPENAI_MAX_TOOL_CALLS", "32"))
        if n > 0:
            lim["max_tool_calls"] = n
    except ValueError:
        pass
    for _ in range(64):
        pl: dict[str, Any] = {"model": m, "input": items, "tools": tools, **lim}
        if os.environ.get("KISS_OPENAI_STORE_FALSE") in ("1", "true"):
            pl["store"] = False
        if prev:
            pl["previous_response_id"] = prev
        hdr = _oai_hdr()
        resp = _oai_poll(_post("https://api.openai.com/v1/responses", pl, hdr, "OpenAI"), hdr)
        prev = resp.get("id") or prev
        last = _oai_txt(resp) or last
        ap = _oai_appr(resp)
        if ap:
            items = ap
            continue
        sf = _sh_fup(resp, ad)
        if sf:
            items = sf
            continue
        st = str(resp.get("status", "completed"))
        if st in ("failed", "cancelled"):
            break
        if st == "incomplete" and str((resp.get("incomplete_details") or {}).get("reason", "")) != "content_filter":
            items = []
            continue
        if st == "incomplete":
            break
        if st in ("queued", "in_progress"):
            items = []
            continue
        if st == "completed" and _pend_out(resp.get("output")):
            items = []
            continue
        break
    text = last or "(sin texto en output)"
    w, d = _bundle(text, "openai")
    return {"final": True, "message": d[: _reply_cap()], "writes": w}
def _bash(cmd: str, to: int, ad: Path | None) -> str:
    cwd = os.environ.get("KISS_BASH_CWD") or (str(ad) if ad else "") or os.getcwd()
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=to)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return f"Error: timeout tras {to}s"
def _ant_build(cfg: dict) -> tuple[list[dict], list[dict], str]:
    t, ms = [], []
    skl = cfg.get("anthropic_skills")
    has_skills = isinstance(skl, list) and len(skl) > 0
    fl = os.environ.get("KISS_ANTHROPIC_TOOLS", "bash,code_execution,mcp").lower()
    if "bash" in fl:
        t.append({"type": "bash_20250124", "name": "bash"})
    if "code_execution" in fl:
        t.append({"type": "code_execution_20250825", "name": "code_execution"})
    elif has_skills:
        t.append({"type": "code_execution_20250825", "name": "code_execution"})
    if "mcp" in fl:
        ms = cfg.get("anthropic_mcp_servers") or []
    b: list[str] = []
    if ms:
        b.append("mcp-client-2025-11-20")
        for s in ms:
            if (n := s.get("name")):
                t.append({"type": "mcp_toolset", "mcp_server_name": n})
    ex = os.environ.get("KISS_ANTHROPIC_BETA_HEADERS", "").strip()
    if ex:
        b.extend(x.strip() for x in ex.split(",") if x.strip())
    if has_skills:
        seenb = {x.lower() for x in b if x}
        for x in ("code-execution-2025-08-25", "skills-2025-10-02"):
            if x.lower() not in seenb:
                seenb.add(x.lower())
                b.append(x)
    return t, ms, ",".join(b)
def call_anthropic(
    *, prompt: str | None = None, context: str, messages: list[dict] | None = None, agent_dir: Path | None = None, tools_cfg: dict | None = None,
) -> dict:
    m = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip()
    mt, ad = int(os.environ.get("KISS_ANTHROPIC_MAX_TOKENS", "8192")), Path(agent_dir).resolve() if agent_dir else None
    cfg = tools_cfg if isinstance(tools_cfg, dict) else {}
    tools, mcp, beta = _ant_build(cfg)
    skills = cfg.get("anthropic_skills")
    skills = skills if isinstance(skills, list) and skills else None
    if messages is not None:
        sys = f"{_HINT}\n\n---\n\n# Carpeta del agente\n\n{context}"
        msgs = [{"role": r, "content": c} for msg in messages if isinstance(msg, dict) and (r := msg.get("role")) in ("user", "assistant") and isinstance(c := msg.get("content"), str)]
    else:
        sys, msgs = _HINT, [{"role": "user", "content": f"{context}\n\n---\n\nUSER_PROMPT:\n{prompt}"}]
    to = int(os.environ.get("KISS_BASH_TIMEOUT", "120"))
    fin = ""
    for _ in range(48):
        pl: dict[str, Any] = {"model": m, "max_tokens": mt, "messages": msgs, "system": sys}
        if tools:
            pl["tools"] = tools
        if mcp:
            pl["mcp_servers"] = mcp
        if skills:
            pl["container"] = {"skills": skills[:8]}
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
    w, d = _bundle(text, "anthropic")
    return {"final": True, "message": d[: _reply_cap()], "writes": w}
_KISS_FILE_HINT = _HINT
_kiss_writes_bundle = _bundle
