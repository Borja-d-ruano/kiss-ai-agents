# Hopx (sandbox) y MCP con agentes KISS

[Hopx](https://hopx.ai) ofrece ejecución de código en contenedores aislados. El servidor MCP oficial está en [hopx-ai/mcp](https://github.com/hopx-ai/mcp) (PyPI `hopx-mcp`).

Si usas **OpenAI Shell en modo local** (`KISS_OPENAI_SHELL_MODE=local` en [`adapters.md`](adapters.md)), los comandos se ejecutan en **tu máquina** (p. ej. `python` local), sin aislamiento de contenedor: sigue siendo útil Hopx cuando necesites **sandbox** o no quieras que el agente toque tu sistema de archivos con privilegios del usuario.

## Transporte: stdio frente a URL HTTP

- **Paquete oficial `hopx-mcp`:** según [`server.json` del repo](https://github.com/hopx-ai/mcp/blob/main/server.json), el despliegue es **`stdio`**: `uvx hopx-mcp` con variable **`HOPX_API_KEY`**. Encaja con **Cursor**, **Claude Desktop**, **VS Code** (`command` + `args` + `env`).
- **KISS con `python main.py run`:** el runtime lee `tools.md` y rellena conectores **OpenAI Remote MCP** y **Anthropic MCP** usando entradas con **`url`** (Streamable HTTP). Eso **no** puede apuntar a un proceso stdio local del mismo modo; hace falta un **servidor MCP HTTP**.

## Dos modos de uso

### 1. IDE local (stdio)

Configura el MCP con `uvx hopx-mcp` y `HOPX_API_KEY`. Útil para desarrollo en el editor; **no** es el canal que usa `main.py run`.

Referencias: [README hopx-ai/mcp](https://github.com/hopx-ai/mcp/blob/main/README.md).

### 2. Agentes KISS (`tools.md` con URL)

Despliega el Worker en **[`cloud/code-executor-mcp`](../cloud/code-executor-mcp/)** (Cloudflare). Expone `/mcp` (Streamable HTTP) y, por dentro, llama a la **API HTTP de Hopx** (`https://api.hopx.dev` por defecto) con la clave solo en **secretos del Worker** (`wrangler secret put HOPX_API_KEY`). En `tools.md` del agente va solo la **URL pública** del Worker, nunca la API key.

Ejemplo neutral:

```json
"mcp_servers": [
  {
    "name": "hopx",
    "url": "https://TU-WORKER.workers.dev/mcp",
    "type": "mcp"
  }
]
```

El runtime mapea esto a `openai_mcp_tools` y `anthropic_mcp_servers`; ver [`adapters.md`](adapters.md).

## Variables de entorno (Hopx)

| Variable | Uso |
|----------|-----|
| `HOPX_API_KEY` | Obligatoria para llamar a la API Hopx (IDE con `uvx` o secret del Worker). |
| `HOPX_BASE_URL` | Opcional; por defecto `https://api.hopx.dev` (también configurable en el Worker). |

## Herramientas MCP oficiales (referencia)

Resumen alineado con el [README](https://github.com/hopx-ai/mcp/blob/main/README.md):

- **Sandboxes:** `create_sandbox`, `list_sandboxes`, `delete_sandbox`, …
- **Código:** `execute_code_isolated` (one-shot recomendado), `execute_code`, modos `isolated` / `persistent` / `rich` / `background`, …
- **Ficheros:** `file_read`, `file_write`, `file_list`, …
- **Comandos:** `run_command`, …

El Worker en `cloud/code-executor-mcp` puede exponer solo un subconjunto (p. ej. `execute_code_isolated`) para mantener la superficie acotada; los nombres y argumentos conviene mantenerlos alineados con el README para que los prompts no diverjan.

## Límites y seguridad (Hopx)

- Ejecución síncrona: hasta **300 s** (documentación Hopx).
- Vida del sandbox: configurable (p. ej. 10 min por defecto en flujos típicos).
- **Internet** en contenedores suele estar **habilitado por defecto**; no ejecutar secretos de cliente sin política clara.
- El endpoint MCP del Worker en plantilla **sin auth** es **público**: en producción usar autenticación (p. ej. [Cloudflare Access / OAuth](https://developers.cloudflare.com/agents/guides/remote-mcp-server/#add-authentication)).

## OpenAI: aprobaciones MCP

Si el proveedor pide confirmación para herramientas MCP, revisa `KISS_OPENAI_MCP_AUTO_APPROVE` y el flujo en `runtime/llm.py` (`_oai_approve`).

## Enlaces

- [hopx-ai/mcp](https://github.com/hopx-ai/mcp)
- [Documentación Hopx](https://docs.hopx.ai)
- [Cloudflare: Remote MCP server](https://developers.cloudflare.com/agents/guides/build-mcp-server/)
- [OpenAI: Remote MCP](https://developers.openai.com/api/docs/guides/tools-remote-mcp)
