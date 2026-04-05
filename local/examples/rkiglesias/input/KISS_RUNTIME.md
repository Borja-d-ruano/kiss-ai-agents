# Runtime KISS + este agente

## Qué hace el cartero

- Todo lo bajo `input/` (incluido este `.md`, `url_publica.py` y **`saas_property_search_tools.json`**) se **concatena al contexto** del modelo. KISS **no** interpreta el Python ni el JSON más allá de incluirlo como texto.
- Las llamadas reales a CRM / propiedades / visitas van por **MCP** (véase el bloque JSON en `tools.md`) o por lo que exponga tu proveedor.

## Gateway HTTP + `run_rk.py`

Desde la **carpeta del agente** (`rkiglesias/`):

`python3 server/kiss_tool_gateway.py`

Luego `python3 run_rk.py "…"` con las variables de **`../CONEXION.md`**.

## Python local (Anthropic + bash en KISS)

Con `KISS_PROVIDER=anthropic`, la herramienta `bash` ejecuta en el host con **cwd = carpeta de este agente** (salvo que definas `KISS_BASH_CWD`).

Ejemplos:

```bash
python3 input/url_publica.py phone "+34 611 22 33 44"
python3 input/url_publica.py url "https://rkcompradores.alt-94.dev/properties/3331"
```

## OpenAI (shell / code interpreter)

El **shell** de OpenAI suele ir en **contenedor remoto** sin tu carpeta montada: ahí **no** podrás ejecutar `input/url_publica.py` tal cual. Usa el código del script como referencia en el propio razonamiento o habilita **MCP** hacia tu backend. Opcional: `KISS_OPENAI_ENABLE_CODE_INTERPRETER=1` para tareas aisladas en el sandbox del proveedor (copiar lógica del `.py` si hace falta).

## Variables útiles (host)

| Variable | Efecto |
|----------|--------|
| `KISS_BASH_CWD` | Directorio de trabajo para bash (por defecto: carpeta del agente). |
| `KISS_OPENAI_ENABLE_CODE_INTERPRETER` | `1` para añadir code interpreter en OpenAI. |
| `KISS_OPENAI_DISABLE_SHELL` | `1` para desactivar shell OpenAI. |
| `KISS_ANTHROPIC_TOOLS` | Por defecto incluye `bash`, `code_execution`, `mcp` (coma-separado). |

Detalle: [`../../../docs/adapters.md`](../../../docs/adapters.md).
