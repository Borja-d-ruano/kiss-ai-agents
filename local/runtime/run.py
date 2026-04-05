from __future__ import annotations

import os
import re
from pathlib import Path
from md_io import (
    apply_writes,
    load_agent,
    read_session_messages,
    resolve_tools_config,
    write_session_messages,
)
from model_adapter import tools_normalizer_fn
_DEFAULT_CONTINUE = (
    "Continúa hasta cumplir done.md con el estado actual de la carpeta; "
    "no repitas preguntas ya resueltas en el historial."
)
def _env_flag(name: str, default: bool) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if not v:
        return default
    return v not in ("0", "false", "no", "off")
def _session_max_messages() -> int:
    try:
        n = int(os.environ.get("KISS_SESSION_MAX_MESSAGES", "48"))
    except ValueError:
        return 48
    return n
def _trim_for_api(msgs: list[dict], max_msgs: int) -> list[dict]:
    if max_msgs <= 0 or len(msgs) <= max_msgs:
        return msgs
    if msgs and msgs[0].get("role") == "user":
        tail_n = max_msgs - 1
        if tail_n <= 0:
            return msgs[-max_msgs:]
        return [msgs[0]] + msgs[-tail_n:]
    return msgs[-max_msgs:]
def _user_facts_block(msgs: list[dict]) -> str:
    blob = "\n".join(str(m.get("content", "")) for m in msgs if m.get("role") == "user")
    if not blob.strip():
        return ""
    name = None
    if m := re.search(
        r"(?:mi nombre es|me llamo|soy)\s+([^\n\.,]{1,80})",
        blob,
        re.I,
    ):
        name = m.group(1).strip()
    phone = None
    for pat in (
        r"(?:tel[ée]fono|m[óo]vil|tlf\.?|whatsapp)\s*[:\s]*([+\d][\d\s\-.]{8,22}\d)",
        r"\b(\d{9})\b",
    ):
        if m2 := re.search(pat, blob, re.I):
            phone = re.sub(r"[\s\-.]", "", m2.group(1))
            break
    lines: list[str] = []
    if name:
        lines.append(f"- Nombre indicado por el usuario: {name}")
    if phone:
        lines.append(f"- Teléfono sugerido en el texto: {phone}")
    if not lines:
        return ""
    return "## Hechos extraídos del historial (sesión)\n" + "\n".join(lines)
def tick_run_fn(root: Path, call_model_fn):
    def f(*, agent_id, prompt):
        sid = f"tick-{agent_id}"
        return {
            "status": "ok",
            "output": "output/stub-last.md",
            "message": run(root / agent_id, prompt, call_model_fn, session_id=sid),
        }
    return f
def run(
    folder,
    prompt,
    call_model,
    max_turns: int | None = None,
    session_id: str | None = None,
) -> str:
    folder = Path(folder)
    sid = (session_id or os.environ.get("KISS_SESSION_ID") or "default").strip() or "default"
    mt = max_turns if max_turns is not None else int(os.environ.get("KISS_MAX_RUN_TURNS", "6"))
    cont = os.environ.get("KISS_CONTINUE_PROMPT", _DEFAULT_CONTINUE).strip() or _DEFAULT_CONTINUE
    tools_cfg = resolve_tools_config(folder, tools_normalizer_fn())
    msgs = read_session_messages(folder, sid)
    msgs.append({"role": "user", "content": str(prompt)})
    last = ""
    max_api = _session_max_messages()
    inc_out = _env_flag("KISS_LOAD_AGENT_OUTPUT", True)
    use_facts = _env_flag("KISS_SESSION_FACTS", True)
    for _ in range(max(1, mt)):
        ctx = load_agent(folder, include_output=inc_out)
        if use_facts and (fb := _user_facts_block(msgs)):
            ctx = fb + "\n\n---\n\n" + ctx
        api_msgs = _trim_for_api(msgs, max_api)
        r = call_model(messages=api_msgs, context=ctx, agent_dir=folder, tools_cfg=tools_cfg)
        apply_writes(folder, r.get("writes") or [])
        last = str(r.get("message", "done"))
        msgs.append({"role": "assistant", "content": last})
        write_session_messages(folder, sid, msgs)
        if r.get("final", True):
            return last
        msgs.append({"role": "user", "content": cont})
    return last or "max turns"
