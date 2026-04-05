from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
def kiss_provider() -> str:
    p = (os.environ.get("KISS_PROVIDER") or "").strip().lower()
    if not p and os.environ.get("KISS_REAL_MODEL"):
        return "openai"
    return p or "stub"
def tools_normalizer_fn():
    p = kiss_provider()
    if p == "openai":
        from llm import normalize_tools_openai
        return normalize_tools_openai
    if p in ("anthropic", "claude"):
        from llm import normalize_tools_anthropic
        return normalize_tools_anthropic
    return None
def call_model(*, prompt: str | None = None, context: str, messages: list | None = None, agent_dir=None, tools_cfg=None, **_kw) -> dict:
    prov = kiss_provider()
    tc = tools_cfg if isinstance(tools_cfg, dict) else {}
    if prov == "openai":
        from llm import call_openai
        return call_openai(prompt=prompt, context=context, messages=messages, agent_dir=agent_dir, tools_cfg=tc)
    if prov in ("anthropic", "claude"):
        from llm import call_anthropic
        return call_anthropic(prompt=prompt, context=context, messages=messages, agent_dir=agent_dir, tools_cfg=tc)
    if prov != "stub":
        raise RuntimeError(f"KISS_PROVIDER desconocido: {prov}")
    p, src = (prompt or "").lower(), prompt or ""
    if messages:
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "user":
                src = str(m.get("content", ""))
                p = src.lower()
                break
    body = "# Respuesta stub\n\n_(stub; KISS_PROVIDER=openai|anthropic + keys)_\n\n## Prompt\n\n" + src[:2000] + "\n"
    w = [{"path": "output/stub-last.md", "content": body}]
    if agent_dir and "KISS:append-heartbeat" in src:
        folder = Path(agent_dir)
        hb = folder / "output" / "heartbeat.md"
        hb.parent.mkdir(parents=True, exist_ok=True)
        prev = hb.read_text(encoding="utf-8") if hb.exists() else "# Heartbeat (schedule)\n\n"
        line = f"- {datetime.now().isoformat(timespec='seconds')} — tick schedule\n"
        w.append({"path": "output/heartbeat.md", "content": prev.rstrip() + "\n" + line + "\n"})
    if any(k in p for k in ("correo", "email", "mail", "resumen")):
        d = datetime.now().strftime("%Y-%m-%d")
        w.append({"path": f"output/resumen-correos-{d}.md", "content": f"# Resumen (stub) — {d}\n\nSin API de correo; salida ficticia.\n"})
    msg = "stub: heartbeat → output/heartbeat.md" if agent_dir and "KISS:append-heartbeat" in src else "stub: listo"
    return {"final": True, "message": msg, "writes": w}
