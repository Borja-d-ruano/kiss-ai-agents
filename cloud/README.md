# KISS Agents — cloud (esqueleto)

Objetivo: misma semántica que `local/` sin duplicar la filosofía.

- Mismo contrato de carpetas / `.md` (ver [`../local/docs/contracts.md`](../local/docs/contracts.md)).
- Mismos endpoints lógicos: `POST /api/run`, `POST /api/tick`.
- El disparador programado lo aporta el proveedor (p. ej. Cloudflare Workers Cron, EventBridge, etc.), no la API de OpenAI ni Anthropic.

Implementación futura: ver [`ADR-cloud.md`](ADR-cloud.md).

## `agents-finder/`

Interfaz web mínima (HTML/CSS/JS) para **navegar y subir ficheros** bajo `KISS_AGENTS_ROOT`, estilo Finder. Requiere el servidor auxiliar de Python en el mismo directorio:

```bash
cd "KISS Agents/cloud/agents-finder"
python3 server.py
```

Abre la URL que imprime (por defecto `http://127.0.0.1:9393/`). Variables: `KISS_AGENTS_ROOT`, `AGENTS_FINDER_HOST`, `AGENTS_FINDER_PORT`.
