# KISS Agents

**Agents as folders of Markdown** — a deliberately minimal **anti-framework**: a tiny **stdlib Python** runtime loads your agent directory, sends context to an AI provider (or a **stub**), applies file `**writes`**, and lets you trigger work with **cron** + `POST /api/tick` or the CLI.

**Design claim:** replace stacks like LangChain for orchestration with **under ~1000 lines** (curretnly 880 lines) of executable code (Python + shell), while your **business logic stays in `.md` and data files**, not in the framework.

---

## Who is this for?


| You are…                                                | Start here                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Product, ops, or “I don’t code”**                     | `[docs/ES-tutorial-kiss-agents-para-todos.md](docs/ES-tutorial-kiss-agents-para-todos.md)` (Spanish) or `[docs/EN-tutorial-kiss-agents-complete.md](docs/EN-tutorial-kiss-agents-complete.md)` (English), **sections 1–13**: what each file does, how to run once, HTTP server, sessions, schedules, examples, FAQ.                                                                           |
| **Developer integrating KISS**                          | Same tutorials **section 14** (technical appendix) + `[local/README.md](local/README.md)` + `[local/docs/adapters.md](local/docs/adapters.md)` + `[local/docs/contracts.md](local/docs/contracts.md)`.                                                                                                                                                                                        |
| **LLM / autonomous agent authoring a new agent folder** | **Section 14 only** in `[docs/ES-tutorial-kiss-agents-para-todos.md](docs/ES-tutorial-kiss-agents-para-todos.md)` or `[docs/EN-tutorial-kiss-agents-complete.md](docs/EN-tutorial-kiss-agents-complete.md)` — canonical file order, JSONL sessions, `tools.md` parsing, OpenAI Responses loop, Anthropic limits, HTTP API, tick rules, MaRK `run_rk` vs `main.py`, checklists, anti-patterns. |


---

## In one minute: what is an “agent”?

- **One folder** under `local/examples/<agent_id>/` (or `KISS_AGENTS_ROOT`).
- **Canonical Markdown files** (all optional except by team convention): `agent.md`, `prompt.md`, `tools.md`, `data.md`, `done.md`, `memory.md`, `steps.md`, `schedule.md`.
- `**input/`** — extra context (`.md`, `.txt`, `.json`, `.csv`, `.py` text-included; **Python is not executed** by KISS on the host by default).
- `**output/`** — generated artifacts; the model can also persist via `**kiss-write**` blocks (see contracts doc).
- `**input/session/**` — **chat history** per session id (JSONL); **ignored** in the normal `load_agent` file crawl so it is not double-fed as a static file.

The runtime is like a **mail carrier**: it does not implement your CRM rules; it **loads**, **calls the model**, and **writes files**.

---

## How to run (quick)

```bash
cd "KISS Agents/local/runtime"

# One-shot (stub by default)
python3 main.py run ../examples/daily-email-summary "Generate a fictitious email summary"

# HTTP server (default :8787): POST /api/run, /api/tick, GET /health
python3 main.py serve

# Scan schedules and run due agents
python3 main.py tick
```

**Real models:** set `KISS_PROVIDER=openai` or `anthropic`, plus API keys — see `[local/README.md](local/README.md)` and `[local/docs/adapters.md](local/docs/adapters.md)`.

**Sessions:** `python3 main.py run ../examples/<agent> "Hello" --session my-chat-id`

---

## Capabilities (what the software can do)

1. **CLI `run`** — single user prompt, optional multi-turn outer loop (`KISS_MAX_RUN_TURNS`, `KISS_CONTINUE_PROMPT`); inner tool orchestration for OpenAI/Anthropic happens inside `call_model`.
2. **HTTP API** — remote trigger, optional `session_id`, `max_turns`, and pre-seed files via `docs` map in JSON body.
3. **Scheduled tick** — `schedule.md` per agent with `**cron**:**,` **tz**:**, `**run**:**, optional` paused:**, `**not_before**:**,` **blackout**:**; external cron calls `tick` or `/api/tick`.
4. **OpenAI Responses** — Shell (hosted/local), optional Code Interpreter, **Remote MCP** from `tools.md` JSON; polling for `queued`/`in_progress`; continuation for `incomplete` and pending tool items; `max_output_tokens` / `max_tool_calls`.
5. **Anthropic Messages** — bash locally; MCP/code_execution expected server-side; see limitations in adapters doc and tutorial §14.
6. **Stub** — offline demo writes to `output/stub-last.md`.
7. **MaRK-style HTTP tools** — example agent `local/examples/rkiglesias` with `**run_rk.py`** + `**server/kiss_tool_gateway.py**` (Chat Completions + POST `/kiss-tools/<name>`), documented in `[local/examples/rkiglesias/CONEXION.md](local/examples/rkiglesias/CONEXION.md)`.
8. **MCP over HTTP for stdio servers** — Cloudflare Worker pattern in `[cloud/code-executor-mcp/](cloud/code-executor-mcp/)`; see `[local/docs/mcp-hopx.md](local/docs/mcp-hopx.md)`.

---

## Repository layout


| Path                                                                              | Role                                                                                       |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `[local/runtime/](local/runtime/)`                                                | `main.py`, `run.py`, `llm.py`, `md_io.py`, `model_adapter.py`, `http_server.py`, `tick.py` |
| `[local/examples/](local/examples/)`                                              | Example agent folders (`daily-email-summary`, `rkiglesias`, `hopx-demo`, …)                |
| `[local/docs/](local/docs/)`                                                      | Philosophy, adapters, contracts, operations, LangChain parity, MCP Hopx                    |
| `[local/scripts/](local/scripts/)`                                                | `install_cron.sh`, `uninstall_cron.sh`                                                     |
| `[docs/](docs/)`                                                                  | **User-facing tutorials** (ES + EN) with AI-oriented appendix                              |
| `[cloud/](cloud/)`                                                                | Cloud-oriented pieces (e.g. `code-executor-mcp` Worker)                                    |
| `[cloud/README.md](cloud/README.md)` / `[cloud/ADR-cloud.md](cloud/ADR-cloud.md)` | Cloud notes and ADR                                                                        |


---

## Documentation index

- **Tutorials (non-technical + §14 for machines):** `[docs/README.md](docs/README.md)`
- **Local developer quickstart:** `[local/README.md](local/README.md)`
- **Philosophy & non-goals:** `[local/docs/philosophy.md](local/docs/philosophy.md)`
- **OpenAI / Anthropic env vars & limits:** `[local/docs/adapters.md](local/docs/adapters.md)`
- `**kiss-write` and response contract:** `[local/docs/contracts.md](local/docs/contracts.md)`
- **Manual test plan, line budget, cron:** `[local/docs/operations.md](local/docs/operations.md)`
- **LangChain conceptual mapping:** `[local/docs/langchain-parity.md](local/docs/langchain-parity.md)`

---

## Source proposal document

Before changing core behavior, read the original analysis (Spanish):

`[analisis-docs/KISS_agents-analisis-y-propuesta.md](../analisis-docs/KISS_agents-analisis-y-propuesta.md)`

---

## License / contributing

To define.