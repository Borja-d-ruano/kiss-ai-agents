from pathlib import Path

from md_io import apply_writes, load_agent


def run(folder, prompt, call_model, max_turns: int = 6) -> str:
    folder = Path(folder)
    task = prompt
    for _ in range(max_turns):
        r = call_model(prompt=task, context=load_agent(folder), agent_dir=folder)
        apply_writes(folder, r.get("writes") or [])
        if r.get("final"):
            return str(r.get("message", "done"))
        task = "Continua desde el estado actual de la carpeta hasta satisfacer done.md."
    return "max turns"
