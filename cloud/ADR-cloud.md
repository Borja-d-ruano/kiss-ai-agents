# ADR: KISS Agents — cloud

## Estado

Aceptado (diseño). Implementación pendiente.

## Contexto

En local, el reloj es **cron del sistema** que hace `curl` a `/api/tick`. Las APIs de modelos no ofrecen scheduling HTTP genérico; los productos tipo Codex/Claude Code llevan su propia orquestación.

## Decisión

1. **Paridad de contratos** con `local/`: un agente sigue siendo una carpeta (o almacenamiento equivalente) de `.md`.
2. **Un solo par de endpoints** en el borde: `run` y `tick`. Sin CRUD de agentes en código propio; los cambios van en markdown (o vía el mismo `run` con un prompt que edite archivos).
3. **Trigger programado externo**: Worker/cron del proveedor invoca `/api/tick` cada minuto (o la cadencia mínima permitida). Sin heartbeats en proceso propio.
4. **Persistencia**: objeto por archivo (R2/S3) o KV indexado por `agent_id` + path; sin ORM ni BBDD relacional para orquestar.

## Consecuencias

- Menos líneas y menos superficie de fallo que colas + workers + BBDD de jobs.
- Hay que diseñar auth y límites de tamaño de payload en el borde.
- El “engine” de cron sigue siendo comparar 5 números contra `schedule.md` (mismo código conceptual que local).
