# KISS Agents — cloud (esqueleto)

Objetivo: misma semántica que `local/` sin duplicar la filosofía.

- Mismo contrato de carpetas / `.md` (ver [`../local/docs/contracts.md`](../local/docs/contracts.md)).
- Mismos endpoints lógicos: `POST /api/run`, `POST /api/tick`.
- El disparador programado lo aporta el proveedor (p. ej. Cloudflare Workers Cron, EventBridge, etc.), no la API de OpenAI ni Anthropic.

Implementación futura: ver [`ADR-cloud.md`](ADR-cloud.md).
