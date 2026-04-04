import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_CRON = re.compile(r"\*\*cron\*\*:\s*(.+)", re.I)
_TZ = re.compile(r"\*\*tz\*\*:\s*(.+)", re.I)
_RUN = re.compile(r"\*\*run\*\*:\s*(.+)", re.I)
_PAUSED = re.compile(r"\*\*paused\*\*:\s*(.+)", re.I)
_NB = re.compile(r"\*\*not_before\*\*:\s*(.+)", re.I)
_BO = re.compile(r"\*\*blackout\*\*:\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", re.I)


def _cron_ok(expr: str, now: datetime) -> bool:
    p = expr.split()
    if len(p) != 5:
        return False
    m, h, dom, mon, dow = p
    for fld, val in (
        (m, now.minute),
        (h, now.hour),
        (dom, now.day),
        (mon, now.month),
        (dow, now.isoweekday() % 7),
    ):
        if fld != "*" and int(fld) != val:
            return False
    return True


def _hist(text: str, row: str) -> str:
    if "## History" not in text:
        text = (
            text.rstrip()
            + "\n\n## History\n\n| Run | Status | Output |\n|-----|--------|--------|\n"
        )
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() != "## History":
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("|"):
            j += 1
        while j < len(lines) and "---" not in lines[j]:
            j += 1
        if j < len(lines):
            lines.insert(j + 1, row)
            return "\n".join(lines) + "\n"
    return text.rstrip() + "\n" + row + "\n"


def _nb_ok(s: str, tz: ZoneInfo, now: datetime) -> bool:
    s = s.strip()
    try:
        if len(s) == 10 and s[4] == "-":
            lim = datetime(int(s[:4]), int(s[5:7]), int(s[8:10]), tzinfo=tz)
        else:
            lim = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if lim.tzinfo is None:
                lim = lim.replace(tzinfo=tz)
        return now >= lim
    except ValueError:
        return True


def _blk(h1: str, h2: str, now: datetime) -> bool:
    def mins(x: str) -> int:
        a, b = x.split(":")
        return int(a) * 60 + int(b)

    n, a, b = now.hour * 60 + now.minute, mins(h1), mins(h2)
    return (a <= n <= b) if a <= b else (n >= a or n <= b)


def tick_all(agents_root: Path, run_fn) -> list[dict]:
    agents_root = Path(agents_root)
    work: list[tuple[Path, str]] = []
    for p in agents_root.rglob("schedule.md"):
        txt = p.read_text(encoding="utf-8")
        if "**cron**:" not in txt.casefold():
            continue
        pm = _PAUSED.search(txt)
        if pm and pm.group(1).strip().lower() in ("true", "yes", "1", "on"):
            continue
        work.append((p, txt))
    if not work:
        return []
    out: list[dict] = []
    for sched, txt in work:
        cm, zm, rm = _CRON.search(txt), _TZ.search(txt), _RUN.search(txt)
        if not (cm and rm):
            continue
        tz = ZoneInfo(zm.group(1).strip() if zm else "UTC")
        now = datetime.now(tz)
        nb = _NB.search(txt)
        if nb and not _nb_ok(nb.group(1), tz, now):
            continue
        bo = _BO.search(txt)
        if bo and _blk(bo.group(1), bo.group(2), now):
            continue
        if not _cron_ok(cm.group(1).strip(), now):
            continue
        aid = sched.parent.name
        r = run_fn(agent_id=aid, prompt=rm.group(1).strip())
        st, op = r.get("status", "ok"), r.get("output", "-")
        row = f"| {now:%Y-%m-%d %H:%M} | {st} | {op} |"
        sched.write_text(_hist(txt, row), encoding="utf-8")
        out.append({"agent_id": aid, "status": st, "output": op})
    return out
