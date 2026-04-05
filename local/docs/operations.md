# Operaciones y presupuesto de líneas

## Conteo (software ejecutable)

Ejecutar desde la raíz del repo:

```bash
wc -l "KISS Agents/local/runtime"/*.py "KISS Agents/local/scripts"/*.sh
```

Presupuesto orientativo (plan original):

| Bloque | Objetivo |
|--------|----------|
| Núcleo runtime (`*.py` salvo `http_server`) | ≤ 250 |
| `http_server.py` | ≤ 120 |
| Scripts shell | ≤ 80 |
| **Total Python + shell** | **≤ 1000** (orientativo; último conteo manual ~**1046**) |

Los `.md` de docs y ejemplos **no** cuentan contra el límite estricto. Si el total supera el presupuesto, recortar o documentar en ADR (véase [`philosophy.md`](philosophy.md)).

## Plan de pruebas manual

1. **Run CLI**
   - `cd "KISS Agents/local/runtime"`
   - `python3 main.py run ../examples/daily-email-summary "resumen de correos diario"`
   - Comprobar que aparecen `output/stub-last.md` y `output/resumen-correos-YYYY-MM-DD.md`.

2. **Servidor + run HTTP**
   - En una terminal: `python3 main.py serve`
   - En otra:  
     `curl -sS -X POST http://127.0.0.1:8787/api/run -H 'content-type: application/json' -d '{"agent_id":"daily-email-summary","prompt":"haz el resumen"}'`

3. **Tick / cron**
   - El ejemplo usa `**cron**: 0 9 * * *` (9:00 Europe/Madrid). Para probar **sin esperar**, edita temporalmente `schedule.md` y pon `**cron**: * * * * *` (cada minuto, v1 solo `*` o enteros).
   - Con el servidor en marcha: `curl -sS -X POST http://127.0.0.1:8787/api/tick`
   - Verifica que `schedule.md` gana una fila nueva en `## History`.
   - Opcional: `./scripts/install_cron.sh` y deja correr el servidor; el sistema disparará `tick` cada minuto.

4. **Health**
   - `curl -sS http://127.0.0.1:8787/health`

5. **Modelo real**
   - Sin `KISS_REAL_MODEL`, siempre stub. Con `KISS_REAL_MODEL=1`, debe implementarse la llamada en `model_adapter.py` (fallará hasta entonces de forma explícita).

## Variables de entorno

| Variable | Uso |
|----------|-----|
| `KISS_AGENTS_ROOT` | Directorio que contiene carpetas de agentes (por defecto `local/examples`). |
| `KISS_HTTP_HOST` / `KISS_HTTP_PORT` | Bind del servidor (`main.py serve` y línea de crontab). |
| `KISS_CRON_EXPRESSION` | Patrón crontab de 5 campos para `install_cron.sh` (defecto `*/5 * * * *`). |
| `KISS_REAL_MODEL` | Compat: sin `KISS_PROVIDER`, fuerza OpenAI. |

Paridad conceptual LangChain vs KISS: [`langchain-parity.md`](langchain-parity.md).
