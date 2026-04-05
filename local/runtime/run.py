from pathlib import Path
from md_io import apply_writes, load_agent, resolve_tools_config
from model_adapter import tools_normalizer_fn
def tick_run_fn(root: Path, call_model_fn):
    def f(*, agent_id, prompt):
        return {"status": "ok", "output": "output/stub-last.md", "message": run(root / agent_id, prompt, call_model_fn)}
    return f
def run(folder, prompt, call_model, max_turns: int = 6) -> str:
    folder = Path(folder)
    tools_cfg = resolve_tools_config(folder, tools_normalizer_fn())
    task = prompt
    for _ in range(max_turns):
        r = call_model(prompt=task, context=load_agent(folder), agent_dir=folder, tools_cfg=tools_cfg)
        apply_writes(folder, r.get("writes") or [])
        if r.get("final"):
            return str(r.get("message", "done"))
        task = "Continua desde el estado actual de la carpeta hasta satisfacer done.md."
    return "max turns"
