# Conexión ejecutable (todo en esta carpeta)

Las 9 tools del comprador se ejecutan contra un **gateway HTTP** incluido aquí (`server/kiss_tool_gateway.py`). El bucle OpenAI + HTTP vive en **`run_rk.py`** (no en `runtime/`).

## URL base

| Entorno | URL típica |
|---------|------------|
| Gateway demo local | `http://127.0.0.1:9876` |
| Health | `GET http://127.0.0.1:9876/health` |
| Tool | `POST http://127.0.0.1:9876/kiss-tools/search_properties` |

Puerto del servidor: **`KISS_GATEWAY_PORT`** (default `9876`).

## Autenticación (usuario / contraseña)

El gateway valida **HTTP Basic** salvo que lo desactives.

| Variable | Rol | Default demo |
|----------|-----|----------------|
| `KISS_GATEWAY_USER` | Usuario que exige el **servidor** | `demo` |
| `KISS_GATEWAY_PASSWORD` | Contraseña del servidor | `demo` |
| `KISS_GATEWAY_DISABLE_AUTH` | `1` → no exige `Authorization` | — |

El **cliente** (`run_rk.py` → gateway) usa:

| Variable | Rol |
|----------|-----|
| `KISS_HTTP_TOOL_BASE_URL` | URL base del gateway (**obligatoria**) |
| `KISS_HTTP_TOOL_USER` / `KISS_HTTP_TOOL_PASSWORD` | Basic hacia el gateway (alinear con `KISS_GATEWAY_*` en demo) |
| `KISS_HTTP_TOOL_BEARER` | Si está definida, sustituye Basic |

OpenAI:

| Variable | Rol |
|----------|-----|
| `OPENAI_API_KEY` | Obligatoria para `run_rk.py` |
| `KISS_OPENAI_CHAT_MODEL` | Opcional (default `gpt-4o-mini` o `OPENAI_MODEL`) |
| `KISS_RK_PUBLIC_BASE` | Base para montar `url` de fichas si la API no la trae (default `https://rkcompradores.alt-94.dev`). |

### API SaaS (gateway → backend)

Si **`KISS_SAAS_API_BASE_URL`** está definida, `kiss_tool_gateway` ejecuta las tools contra esa API (`GET /api/properties`, `GET /api/properties/search`, `POST /api/contactos/create`, `POST /api/demands`, `GET/POST /api/gestiones*`, etc.), alineado con `rag-api/api-properties.md` y las acciones MCP. Si no está definida, el gateway sigue en **modo demo** (datos falsos).

| Variable | Rol |
|----------|-----|
| `KISS_SAAS_API_BASE_URL` | Origen HTTPS del sitio/API (sin barra final). Ej. `https://rkcompradores.alt-94.dev` |
| `KISS_SAAS_API_TOKEN` | Token máquina (normalmente `Authorization: Bearer …`). Obligatorio para búsqueda por id, contactos, demandas y gestiones si el despliegue lo exige. |
| `KISS_SAAS_USE_X_API_TOKEN` | `1` → enviar `X-API-Token` en lugar de Bearer (según `api-properties.md`). |
| `KISS_SAAS_SEARCH_LIMIT` | Límite en listado (default `12`). |
| `KISS_SAAS_HTTP_TIMEOUT` | Timeout segundos del gateway hacia el SaaS (default `120`). |
| `KISS_HTTP_TOOL_TIMEOUT` | Timeout de `run_rk.py` hacia el gateway en segundos (default `180`; debe ser mayor que el tiempo real del SaaS). |

Detalle de cabeceras y paths editables: `server/saas_backend.py` (docstring).

## Dos terminales

**Terminal A — gateway** (working directory = carpeta de este agente):

```bash
cd "/ruta/a/KISS Agents/local/examples/rkiglesias"
python3 server/kiss_tool_gateway.py
```

**Terminal B — agente**

```bash
cd "/ruta/a/KISS Agents/local/examples/rkiglesias"
export KISS_HTTP_TOOL_BASE_URL=http://127.0.0.1:9876
export KISS_HTTP_TOOL_USER=demo
export KISS_HTTP_TOOL_PASSWORD=demo
export OPENAI_API_KEY="sk-..."
export KISS_OPENAI_CHAT_MODEL=gpt-4o-mini
python3 run_rk.py "Busca pisos en Oviedo y cuéntame la primera opción"
```

## Fichero de variables de ejemplo

[`connection.example.env`](connection.example.env)

## Enlazar con el SaaS real

Configura **`KISS_SAAS_API_BASE_URL`** y **`KISS_SAAS_API_TOKEN`** (ver tabla anterior). No hace falta otro proxy: el gateway ya implementa las llamadas. Los nombres de tool deben coincidir con `input/saas_property_search_tools.json`.

## `main.py run` genérico (sin `run_rk.py`)

Si prefieres el runner estándar de KISS (`python main.py run …` desde `local/runtime`), configura MCP en `tools.md` y usa `KISS_PROVIDER=openai` o `anthropic`; ese flujo **no** usa el gateway local salvo que expongas un servidor MCP compatible.
