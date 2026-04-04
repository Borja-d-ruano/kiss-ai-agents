"""OpenAI Responses + Anthropic Messages (urllib stdlib). MCP desde bloque JSON en tools.md."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from md_io import parse_or_normalize_tools_md


def _req(url: str, data: dict, headers: dict[str, str], who: str = "") -> dict:
    r = urllib.request.Request(
        url, data=json.dumps(data).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        p = f"{who} " if who else ""
        raise RuntimeError(f"{p}HTTP {e.code}: {e.read().decode(errors='replace')}") from e


def _hdr_oai() -> dict[str, str]:
    k = os.environ.get("OPENAI_API_KEY", "").strip()
    if not k:
        raise RuntimeError("Falta OPENAI_API_KEY")
    return {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}


def _hdr_ant(beta: str) -> dict[str, str]:
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
                    out.append(
                        {
                            "type": "mcp_approval_response",
                            "approve": True,
                            "approval_request_id": aid,
                        }
                    )
            for v in o.values():
                sc(v)
        elif isinstance(o, list):
            for x in o:
                sc(x)

    sc(resp)
    return out


def _norm_oai(raw: str) -> str:
    m = os.environ.get("OPENAI_MODEL", "gpt-5").strip()
    return _oai_txt(
        _req(
            "https://api.openai.com/v1/responses",
            {
                "model": m,
                "input": [
                    {
                        "role": "system",
                        "content": (
                            'Corrige tools.md → SOLO JSON válido {"openai_mcp_tools":[],"anthropic_mcp_servers":[]} '
                            "sin markdown; arrays vacíos si falta data."
                        ),
                    },
                    {"role": "user", "content": raw[:12000]},
                ],
            },
            _hdr_oai(),
            "OpenAI",
        )
    )


def _oai_tools(ad: Path | None) -> list[dict]:
    o: list[dict] = []
    if os.environ.get("KISS_OPENAI_DISABLE_SHELL") not in ("1", "true", "yes"):
        o.append({"type": "shell", "environment": {"type": "container_auto"}})
    if os.environ.get("KISS_OPENAI_ENABLE_CODE_INTERPRETER") in ("1", "true", "yes"):
        o.append(
            {
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "memory_limit": os.environ.get("KISS_OPENAI_CI_MEMORY", "4g"),
                },
            }
        )
    o.extend((parse_or_normalize_tools_md(ad, _norm_oai) or {}).get("openai_mcp_tools") or [])
    return o


def call_openai(*, prompt: str, context: str, agent_dir: Path | None = None) -> dict:
    m = os.environ.get("OPENAI_MODEL", "gpt-5").strip()
    ad = Path(agent_dir).resolve() if agent_dir else None
    tools = _oai_tools(ad)
    sys = os.environ.get(
        "KISS_OPENAI_INSTRUCTIONS",
        "Eres KISS Agents; usa tools si hace falta; el host guarda salida en output/.",
    )
    body = f"{context}\n\n---\n\nUSER_PROMPT:\n{prompt}"
    items: Any = [{"role": "system", "content": sys}, {"role": "user", "content": body}]
    prev, last = None, ""
    for _ in range(32):
        pl: dict = {"model": m, "input": items, "tools": tools}
        if os.environ.get("KISS_OPENAI_STORE_FALSE") in ("1", "true"):
            pl["store"] = False
        if prev:
            pl = {"model": m, "previous_response_id": prev, "input": items}
        resp = _req("https://api.openai.com/v1/responses", pl, _hdr_oai(), "OpenAI")
        prev = resp.get("id") or prev
        last = _oai_txt(resp) or last
        st = str(resp.get("status", "completed"))
        if st in ("completed", "failed", "cancelled"):
            break
        ap = _oai_approve(resp)
        if ap:
            items = ap
            continue
        break
    text = last or "(sin texto en output)"
    return {"final": True, "message": text[:2000], "writes": [{"path": "output/openai-last.md", "content": text}]}


def _bash(cmd: str, to: int, ad: Path | None) -> str:
    cwd = os.environ.get("KISS_BASH_CWD") or (str(ad) if ad else "") or os.getcwd()
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=to)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return f"Error: timeout tras {to}s"


def _norm_ant(raw: str) -> str:
    m = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip()
    r = _req(
        "https://api.anthropic.com/v1/messages",
        {
            "model": m,
            "max_tokens": 2048,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        'SOLO JSON {"openai_mcp_tools":[],"anthropic_mcp_servers":[]} sin markdown.\n\n'
                        + raw[:12000]
                    ),
                }
            ],
        },
        _hdr_ant(""),
        "Anthropic",
    )
    return "\n".join(
        str(b.get("text", "")) for b in r.get("content") or [] if b.get("type") == "text"
    ).strip()


def _ant_build(ad: Path | None) -> tuple[list[dict], list[dict], str]:
    t, ms, b = [], [], []
    cfg = parse_or_normalize_tools_md(ad, _norm_ant)
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


def call_anthropic(*, prompt: str, context: str, agent_dir: Path | None = None) -> dict:
    m = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929").strip()
    mt = int(os.environ.get("KISS_ANTHROPIC_MAX_TOKENS", "8192"))
    ad = Path(agent_dir).resolve() if agent_dir else None
    tools, mcp, beta = _ant_build(ad)
    ut = f"{context}\n\n---\n\nUSER_PROMPT:\n{prompt}"
    msgs: list[dict] = [{"role": "user", "content": ut}]
    to = int(os.environ.get("KISS_BASH_TIMEOUT", "120"))
    fin = ""
    for _ in range(48):
        pl: dict = {"model": m, "max_tokens": mt, "messages": msgs}
        if tools:
            pl["tools"] = tools
        if mcp:
            pl["mcp_servers"] = mcp
        resp = _req("https://api.anthropic.com/v1/messages", pl, _hdr_ant(beta), "Anthropic")
        content = resp.get("content") or []
        fin = (
            "\n".join(str(b.get("text", "")) for b in content if b.get("type") == "text").strip()
            or fin
        )
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
                out = (
                    "Bash session restart (stub local: no stateful shell)"
                    if inp.get("restart")
                    else _bash(str(inp.get("command", "")), to, ad)
                )
                tr.append({"type": "tool_result", "tool_use_id": tid, "content": out})
            else:
                tr.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tid,
                        "content": f"(KISS) `{nm}` no en cliente; code_execution/MCP server-side.",
                        "is_error": True,
                    }
                )
        if not tr:
            break
        msgs += [{"role": "assistant", "content": content}, {"role": "user", "content": tr}]
    text = fin or "(sin texto en output)"
    return {"final": True, "message": text[:2000], "writes": [{"path": "output/anthropic-last.md", "content": text}]}
