# Contratos markdown por agente

Cada agente es un directorio bajo `examples/<agent_id>/` (o la ruta que defina `KISS_AGENTS_ROOT`).

## Archivos canónicos (todos opcionales salvo convención del equipo)

| Archivo | Rol |
|---------|-----|
| `agent.md` | Identidad, límites, tono. Mínimo recomendado. |
| `prompt.md` | Instrucciones base del agente. |
| `tools.md` | Herramientas permitidas (MCP, HTTP, etc.) + bloque JSON canónico para wiring real. |
| `data.md` | Datos de contexto o dónde encontrarlos. |
| `done.md` | Criterio de terminación (el modelo debe honrarlo al devolver `final`). |
| `memory.md` | Persistencia vía **`kiss-write`** en la respuesta del modelo (parseada en `llm.py`); el runtime aplica todos los `writes` devueltos por el adaptador. Ver abajo. |
| `steps.md` | Plan / estado de ejecución. |
| `schedule.md` | Programación: `**cron**`, `**tz**`, `**run**`, opcional `**paused**`, `**not_before**` (fecha `YYYY-MM-DD` o ISO), `**blackout**` (`HH:MM-HH:MM` en `tz`, cruza medianoche si inicio > fin), tabla `## History`. |

## `memory.md` entre runs (varios `run` / varios mensajes)

OpenAI y Anthropic reciben en sistema la convención **`kiss-write`**: bloques en el texto de salida con rutas relativas al agente. `llm.py` los convierte en entradas extra de `writes` junto a `output/<provider>-last.md` (texto sin esos bloques).

````markdown
```kiss-write path=memory.md
# Memoria
…contenido completo…
```
````

Rutas con `..` o absolutas se ignoran. Lo escrito solo en el **sandbox** del proveedor (`sandbox:/mnt/data/…`) no llega al disco local salvo que el modelo reproduzca el contenido en un `kiss-write`.

## Carpetas

- `input/` — entradas del usuario o adjuntos.
- `output/` — artefactos generados (el modelo escribe aquí vía `writes`).

## Respuesta del modelo (contrato técnico)

`call_model` devuelve un dict:

```python
{
  "final": bool,
  "message": str,
  "writes": [{"path": "output/x.md", "content": "..."}],
}
```

## Cron en `schedule.md` (v1)

- Línea `**cron**:` con 5 campos separados por espacio: `min hour dom mon dow`.
- Cada campo es `*` o un entero.
- `dow`: `0` = domingo, … `6` = sábado (alineado con `datetime.isoweekday() % 7`).

El disparador externo (crontab) define cada cuánto se llama a `/api/tick`; `**cron**:` filtra si en ese minuto corresponde ejecutar el agente.
