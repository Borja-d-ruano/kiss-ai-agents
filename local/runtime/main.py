import argparse
import os
from pathlib import Path


def _ex() -> Path:
    return (Path(__file__).resolve().parent.parent / "examples").resolve()


def main() -> None:
    ap = argparse.ArgumentParser(description="KISS Agents local (stdlib)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    pr = sp.add_parser("run")
    pr.add_argument("folder", type=Path)
    pr.add_argument("prompt")
    pr.add_argument("--max-turns", type=int, default=6)
    pt = sp.add_parser("tick")
    pt.add_argument("--root", type=Path, default=None)
    ps = sp.add_parser("serve")
    ps.add_argument("--host", default=os.environ.get("KISS_HTTP_HOST", "127.0.0.1"))
    ps.add_argument("--port", type=int, default=int(os.environ.get("KISS_HTTP_PORT", "8787")))
    a = ap.parse_args()
    if a.cmd == "run":
        from model_adapter import call_model
        from run import run

        print(run(Path(a.folder).resolve(), a.prompt, call_model, max_turns=a.max_turns))
    elif a.cmd == "tick":
        from model_adapter import call_model
        from run import run
        from tick import tick_all

        root = Path(a.root).resolve() if a.root else _ex()

        def run_fn(*, agent_id, prompt):
            return {
                "status": "ok",
                "output": "output/stub-last.md",
                "message": run(root / agent_id, prompt, call_model),
            }

        print(tick_all(root, run_fn))
    else:
        os.environ.setdefault("KISS_AGENTS_ROOT", str(_ex()))
        from http_server import serve

        serve(a.host, a.port)


if __name__ == "__main__":
    main()
