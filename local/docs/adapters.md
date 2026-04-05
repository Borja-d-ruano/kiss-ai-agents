# Adaptadores OpenAI y Anthropic (stdlib)

Implementación: `runtime/llm.py` (OpenAI + Anthropic en un módulo); despacho en `model_adapter.py`. `tools.md` se resuelve **una vez** al inicio de `run()` vía `md_io.resolve_tools_config`.

Para una línea futura **agnóstica** (HTTP tools genérico, Python vía proveedor, límites), ver [`philosophy.md`](philosophy.md) → *Extensiones del runtime*.

## Activación

| Variable | Valor |
|----------|--------|
| `KISS_PROVIDER` | `stub` (defecto), `openai`, `anthropic` o `claude` |
| `KISS_REAL_MODEL` | Si es `1` y no hay `KISS_PROVIDER`, equivale a `openai` (compat). |

## MCP y tools: fuente canónica `tools.md`

Por filosofía del proyecto, la **configuración declarativa** de MCP vive en `tools.md` con un bloque:

```json
{
  "openai_mcp_tools": [],
  "anthropic_mcp_servers": [],
  "mcp_servers": []
}
```

`mcp_servers` (opcional) es lista neutral `{ "name", "url", "type" }`; se **mapea** a entradas en las dos listas de proveedor. Para **OpenAI Responses** (Remote MCP), `llm.py` normaliza a `server_label` + `server_url` y el bucle sigue tras `mcp_approval_request` aunque `status` sea `completed`. El runtime, **al arrancar cada `run`**:

1. extrae el primer bloque ` ```json ... ``` ` de `tools.md`,
2. parsea y valida listas,
3. aplica `mcp_servers` → openai / anthropic,
4. si el JSON falla, **una** normalización con el proveedor activo (si hay),
5. si sigue fallando, escribe `output/tools-md-invalid.md` y usa config vacía.

## OpenAI (Responses API)

| Variable | Descripción |
|----------|-------------|
| `OPENAI_API_KEY` | Obligatorio. |
| `OPENAI_MODEL` | Por defecto `gpt-5.4` (documentación oficial de [hosted Shell](https://developers.openai.com/api/docs/guides/tools-shell) usa ese id). Otro modelo puede no admitir `shell` / `code_interpreter`. |
| `KISS_OPENAI_INSTRUCTIONS` | Instrucciones de sistema (opcional). |
| `KISS_OPENAI_DISABLE_SHELL` | `1` desactiva la herramienta Shell (hosted y local). |
| `KISS_OPENAI_SHELL_MODE` | `hosted` (defecto): Shell con `container_auto`. `local`: solo `{"type":"shell"}`; el runtime ejecuta `shell_call` en la máquina del cliente y reenvía `shell_call_output` (véase [local shell mode](https://developers.openai.com/api/docs/guides/tools-shell#local-shell-mode)). `off` / `none` / `false` / `0`: sin Shell. |
| `KISS_OPENAI_ENABLE_CODE_INTERPRETER` | `1` añade Code Interpreter. |
| `KISS_OPENAI_CI_MEMORY` | P.ej. `4g`. |
| `KISS_OPENAI_MCP_AUTO_APPROVE` | `1` (defecto) auto-aprobación MCP heurística. |
| `KISS_OPENAI_STORE_FALSE` | `1` → `store: false`. |

Referencias: [Shell](https://developers.openai.com/api/docs/guides/tools-shell), [Code Interpreter](https://developers.openai.com/api/docs/guides/tools-code-interpreter), [Remote MCP](https://developers.openai.com/api/docs/guides/tools-remote-mcp).

Para **Hopx** (ejecución aislada en la nube): el servidor MCP PyPI es **stdio**; con KISS y `url` en `tools.md` se usa el Worker en [`cloud/code-executor-mcp`](../cloud/code-executor-mcp/) — ver [`mcp-hopx.md`](mcp-hopx.md). **Shell en modo `local`** corre en tu sistema con los mismos permisos que el proceso de `main.py`; no sustituye un sandbox como Hopx.

## Anthropic (Messages API)

| Variable | Descripción |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Obligatorio. |
| `ANTHROPIC_MODEL` | Por defecto `claude-sonnet-4-5-20250929`. |
| `KISS_ANTHROPIC_MAX_TOKENS` | Por defecto `8192`. |
| `KISS_ANTHROPIC_TOOLS` | `bash`, `code_execution`, `mcp` (coma). |
| `KISS_ANTHROPIC_BETA_HEADERS` | Betas extra. |
| `KISS_BASH_CWD` | Override del cwd del bash local. |
| `KISS_BASH_TIMEOUT` | Segundos (defecto `120`). |

Referencias: [MCP connector](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector) (`mcp-client-2025-11-20`), [Bash](https://platform.claude.com/docs/en/agents-and-tools/tool-use/bash-tool), [Code execution](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool).

## Limitaciones actuales

- Salida principal en `output/*-last.md`. Sin descarga automática de ficheros del contenedor OpenAI.
- Rutas `sandbox:/mnt/data/...` en el texto del modelo: entorno alojado, **no** tu carpeta. Para persistir aquí, el modelo debe emitir bloques **`kiss-write`** (parseados en `llm.py` → `writes`); ver [`contracts.md`](contracts.md).
- Bucle OpenAI: follow-ups por aprobaciones MCP (heurística), por `shell_call` en modo `local` (`shell_call_output` + `previous_response_id`), y comprobación de `status`.
- Anthropic: solo `bash` se ejecuta en local; el resto depende del servidor / MCP remoto.

## Cron del sistema

- `install_cron.sh` usa `KISS_CRON_EXPRESSION` (defecto `*/5 * * * *`). Sin lógica extra en Python.
- `tick` hace una sola pasada por `schedule.md`: sin `**cron**:` activo → no ejecuta `run_fn` (lista vacía).
