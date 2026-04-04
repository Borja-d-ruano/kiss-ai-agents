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
| `memory.md` | Memoria resumida persistente. |
| `steps.md` | Plan / estado de ejecución. |
| `schedule.md` | Programación: `**cron**`, `**tz**`, `**run**`, opcional `**paused**`, `**not_before**` (fecha `YYYY-MM-DD` o ISO), `**blackout**` (`HH:MM-HH:MM` en `tz`, cruza medianoche si inicio > fin), tabla `## History`. |

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
