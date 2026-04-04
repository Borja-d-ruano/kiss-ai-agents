from __future__ import annotations

import json
from pathlib import Path

AGENT_FILES = (
    "agent.md",
    "prompt.md",
    "tools.md",
    "data.md",
    "done.md",
    "memory.md",
    "steps.md",
    "schedule.md",
)


def load_agent(folder: Path) -> str:
    folder = Path(folder)
    parts: list[str] = []
    for name in AGENT_FILES:
        p = folder / name
        if p.exists() and (t := p.read_text(encoding="utf-8").strip()):
            parts.append(f"# {name}\n\n{t}")
    for sub in ("input", "output"):
        d = folder / sub
        if d.exists():
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.suffix in (".md", ".txt", ".json", ".csv"):
                    parts.append(f"# {f.relative_to(folder)}\n\n{f.read_text(encoding='utf-8')}")
    return "\n\n---\n\n".join(parts)


def apply_writes(folder: Path, writes: list) -> None:
    folder = Path(folder)
    for w in writes:
        path = folder / w["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(w.get("content", ""), encoding="utf-8")


def parse_or_normalize_tools_md(agent_dir: Path | str | None, normalizer=None) -> dict:
    if not agent_dir:
        return {}
    p = Path(agent_dir) / "tools.md"
    if not p.exists():
        return {}
    raw = p.read_text(encoding="utf-8")
    s, e = raw.find("```json"), -1
    if s >= 0:
        e = raw.find("```", s + 7)
    cand = raw[s + 7 : e].strip() if s >= 0 and e > s else ""

    def pv(txt: str) -> dict:
        o = json.loads(txt)
        if not isinstance(o, dict):
            return {}
        out = dict(o)
        for k in ("openai_mcp_tools", "anthropic_mcp_servers"):
            v = out.get(k)
            if k in out and not isinstance(v, list):
                out[k] = []
            if isinstance(out.get(k), list):
                cl = []
                for it in out[k]:
                    if not isinstance(it, dict):
                        continue
                    t, n, u = str(it.get("type", "")).strip(), str(it.get("name", "")).strip(), str(
                        it.get("url", it.get("server_url", ""))
                    ).strip()
                    if t and (n or u):
                        cl.append(it)
                out[k] = cl
        return out

    try:
        if cand:
            return pv(cand)
    except json.JSONDecodeError:
        pass
    if callable(normalizer) and isinstance(fx := normalizer(raw), str) and fx.strip():
        try:
            return pv(fx.strip())
        except json.JSONDecodeError:
            pass
    return {}
