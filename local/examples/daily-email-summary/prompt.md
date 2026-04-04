# Prompt base

## Qué NO es memoria

- `output/openai-last.md` (o `anthropic-last.md`) lo rellena el **adaptador** en cada `run` con tu texto **visible** (sin bloques `kiss-write`). **Solo guarda la última respuesta**; el turno anterior desaparece de ahí. **No uses ese archivo como historial** ni asumas que “el usuario dijo X” si X no está en `memory.md` o en otro fichero que tú hayas escrito con `kiss-write`.

## Obligación en **todo** cierre (`final: true`)

Sin excepción (salvo que el usuario pida explícitamente **no** registrar nada en memoria):

1. Incluye **al menos un** bloque `kiss-write path=memory.md`.
2. El contenido del fichero debe ser **íntegro**: copia **todo** el `memory.md` que ya venía en el contexto y **añade al final** un bloque nuevo:

```markdown
### <fecha y hora en texto, p. ej. 2026-04-04 18:40 local>

**Usuario:** <cita fiel del USER_PROMPT de este turno; si es largo, un resumen“…”>
**Asistente:** <tu respuesta al usuario en prosa, o resumen fiel si fue muy larga>
```

3. Si el usuario pide **borrar o reiniciar** la memoria, `kiss-write path=memory.md` con el mínimo acordado (p. ej. solo `# Memoria` y una línea explicando el reinicio).

Así el siguiente `run` tiene **huella literal** de lo dicho, sin depender del `-last.md` ni del sandbox.

## Convención `kiss-write`

Formato exacto y advertencia sobre `sandbox:`: ver mensaje de sistema y `docs/contracts.md`.

## Tareas de este ejemplo (correo)

1. Lee `tools.md` y `data.md`.
2. **Solo** si el usuario pide explícitamente correo / resumen de buzón, genera o actualiza un markdown claro en `output/` (p. ej. resumen diario).
3. Si la petición es conversación, datos o preguntas sin relación con el correo, **no** fuerces un `resumen-correos-*.md`; basta con responder bien y **cumplir la obligación de `memory.md`**.
