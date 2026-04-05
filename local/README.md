# KISS Agents — local

## Requisitos

- Python 3.9+ (usa `zoneinfo`; en Windows 3.9+ incluye tzdata cuando hace falta).

## Tres comandos rápidos

```bash
cd "KISS Agents/local/runtime"

# 1) Ejecutar un agente por carpeta (stub del modelo por defecto)
python main.py run ../examples/daily-email-summary "Genera el resumen de correo (stub)"

# 2) Servidor HTTP (por defecto :8787)
python main.py serve

# 3) Tick manual (escanea schedules bajo examples/)
python main.py tick
```

## Cron Unix (una línea)

Por defecto el script instala `*/5 * * * *` (cada 5 min). Otro patrón:

```bash
export KISS_CRON_EXPRESSION="0 9 * * *"
../scripts/install_cron.sh
```

Con el servidor en marcha:

```bash
../scripts/install_cron.sh
```

Quitar:

```bash
../scripts/uninstall_cron.sh
```

## Modelo real (OpenAI / Anthropic)

Por defecto: **stub** (`KISS_PROVIDER` vacío o `stub`).

- **OpenAI** (Responses API: Shell, Code Interpreter, MCP remoto desde bloque JSON en `tools.md`):

  ```bash
  export KISS_PROVIDER=openai
  export OPENAI_API_KEY=...
  export OPENAI_MODEL=gpt-5.4
  ```

- **Anthropic** (Messages: bash local, code_execution server-side, MCP remoto desde `tools.md`):

  ```bash
  export KISS_PROVIDER=anthropic
  export ANTHROPIC_API_KEY=...
  export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
  ```

Variables detalladas: [`docs/adapters.md`](docs/adapters.md).

- **Varios ficheros en disco:** OpenAI/Anthropic incluyen la convención `kiss-write` en sistema; el adaptador vuelca esos bloques en `writes` además de `output/*-last.md`. Ver [`docs/contracts.md`](contracts.md). El **stub** no genera `kiss-write` (solo sus `writes` fijos).

## Ejemplos

- [`examples/daily-email-summary`](examples/daily-email-summary) — resumen de correo y memoria con `kiss-write`.
- [`examples/rkiglesias`](examples/rkiglesias) — MaRK; tools HTTP ejecutables con `run_rk.py` dentro de la carpeta del agente (ver [`examples/rkiglesias/CONEXION.md`](examples/rkiglesias/CONEXION.md)).

Compat: `KISS_REAL_MODEL=1` sin `KISS_PROVIDER` → se usa OpenAI.
