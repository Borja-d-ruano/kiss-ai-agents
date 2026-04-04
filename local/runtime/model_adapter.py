import os
from datetime import datetime


def call_model(*, prompt: str, context: str, agent_dir=None, **_kw) -> dict:
    prov = (os.environ.get("KISS_PROVIDER") or "").strip().lower()
    if not prov and os.environ.get("KISS_REAL_MODEL"):
        prov = "openai"
    if prov == "openai":
        from llm import call_openai

        return call_openai(prompt=prompt, context=context, agent_dir=agent_dir)
    if prov in ("anthropic", "claude"):
        from llm import call_anthropic

        return call_anthropic(prompt=prompt, context=context, agent_dir=agent_dir)
    if prov and prov != "stub":
        raise RuntimeError(f"KISS_PROVIDER desconocido: {prov}")
    p = (prompt or "").lower()
    body = (
        "# Respuesta stub\n\n_(stub; KISS_PROVIDER=openai|anthropic + keys)_\n\n## Prompt\n\n"
        f"{prompt[:2000]}\n"
    )
    w = [{"path": "output/stub-last.md", "content": body}]
    if any(k in p for k in ("correo", "email", "mail", "resumen")):
        d = datetime.now().strftime("%Y-%m-%d")
        w.append(
            {
                "path": f"output/resumen-correos-{d}.md",
                "content": f"# Resumen (stub) — {d}\n\nSin API de correo; salida ficticia.\n",
            }
        )
    return {"final": True, "message": "stub: listo", "writes": w}
