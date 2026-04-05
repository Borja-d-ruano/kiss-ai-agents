# KISS Agents - An agent anti-framework "framework"

Runtime mínimo (stdlib Python) para agentes como **carpetas de markdown**: carga contexto, llama al modelo, persiste `.md`, y dispara tareas con **cron Unix** + `POST /api/tick`.

**Claim:** sustituir LangChain por menos de 1000 líneas de software ejecutable.

## Guía para personas no técnicas

- [`docs/tutorial-kiss-agents-para-todos.md`](docs/tutorial-kiss-agents-para-todos.md) — tutorial detallado: cada `.md`, modos de uso, ejemplos y diagramas.

## Estructura

- [`local/`](local/) — implementación local-first (runner, HTTP, cron).
- [`cloud/`](cloud/) — esqueleto y ADR para paridad cloud (sin runtime cloud aún).
- [`docs/`](docs/) — documentación orientada a usuario (tutorial) e índice.

## Documento fuente

Antes de tocar código, leer:

[`analisis-docs/KISS_agents-analisis-y-propuesta.md`](../analisis-docs/KISS_agents-analisis-y-propuesta.md)
