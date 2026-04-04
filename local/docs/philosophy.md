# Filosofía KISS Agents (reglas no negociables)

Sintetizado desde [`../../../analisis-docs/KISS_agents-analisis-y-propuesta.md`](../../../analisis-docs/KISS_agents-analisis-y-propuesta.md). Si el código contradice esto, gana el documento.

## Lo que NO hacemos

| Regla | Motivo |
|-------|--------|
| Sin BBDD para orquestar agentes | El filesystem (carpeta del agente) es el estado. |
| Sin librerías de agentes / scheduling | LangChain, APScheduler, Bull, etc. añaden abstracción y mantenimiento. |
| Sin heartbeats ni daemons de polling | El reloj es **cron** (o `curl` periódico), no un proceso residente preguntando. |
| Sin “procesar negocio” en nuestro código | No NLP, clasificación ni extracción en el backend; eso lo hace el modelo. |
| Menos de ~1000 líneas de software ejecutable | Si crece más, recortar o justificar con ADR. |

## Lo que SÍ hacemos

1. **Enviar markdown al modelo** (contexto = contenidos de la carpeta).
2. **Recibir markdown del modelo** (respuesta estructurada con `writes` a archivos).

El backend es un **cartero** de `.md`.

## Principios operativos

- Un agente = una carpeta con `.md` (+ `input/`, `output/`). El wiring máquina-legible de MCP va en bloque JSON dentro de `tools.md`.
- Markdown = control-plane (`prompt.md`, `tools.md`, `schedule.md`, `memory.md`, `steps.md`, `done.md`).
- El modelo = runtime de razonamiento (en prod: API real; en demo: stub).
- Scheduling = `schedule.md` + comparación trivial de cron + disparador externo.
