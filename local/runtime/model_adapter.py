import os
from datetime import datetime
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
def call_model(*, prompt: str, context: str, agent_dir=None, tools_cfg=None, **_kw) -> dict:
    prov = kiss_provider()
    tc = tools_cfg if isinstance(tools_cfg, dict) else {}
    if prov == "openai":
        from llm import call_openai
        return call_openai(prompt=prompt, context=context, agent_dir=agent_dir, tools_cfg=tc)
    if prov in ("anthropic", "claude"):
        from llm import call_anthropic
        return call_anthropic(prompt=prompt, context=context, agent_dir=agent_dir, tools_cfg=tc)
    if prov != "stub":
        raise RuntimeError(f"KISS_PROVIDER desconocido: {prov}")
    p = (prompt or "").lower()
    body = "# Respuesta stub\n\n_(stub; KISS_PROVIDER=openai|anthropic + keys)_\n\n## Prompt\n\n" f"{prompt[:2000]}\n"
    w = [{"path": "output/stub-last.md", "content": body}]
    if any(k in p for k in ("correo", "email", "mail", "resumen")):
        d = datetime.now().strftime("%Y-%m-%d")
        w.append({"path": f"output/resumen-correos-{d}.md", "content": f"# Resumen (stub) — {d}\n\nSin API de correo; salida ficticia.\n"})
    return {"final": True, "message": "stub: listo", "writes": w}
