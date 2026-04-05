# Investigación: herramientas del agente comprador (SaaS)

Ruta del código: `saas-platform-rk-all-fresh/rag-api/`.

## Catálogo y riesgo (manifest)

Fichero: `agents/tools/tool_manifest.py`.

| Nombre expuesto al LLM (registry) | Categoría | Riesgo (manifest) | Confirmación por defecto |
| --- | --- | --- | --- |
| `search_properties` | property | low | no |
| `property_details` | property | low | no |
| `property_interest` | property | medium | no |
| `search_contact` | contact | medium | no |
| `create_contact` | contact | high | no |
| `check_availability` *(clave en manifest)* | scheduling | low | no |
| `schedule_visit` | scheduling | high | sí |
| `cancel_visit` | scheduling | high | sí |
| `create_demand` | demand | high | no |

En el manifest, la clave interna de disponibilidad es **`check_availability`**; el **nombre de la función LangChain** que ejecuta la acción MCP es **`check_agent_availability`** (`agents/tools/mcp_tools.py`). El `agent_executor_service` mapea `check_availability` → herramienta registry `check_agent_availability`.

## Implementación LangChain (subset en `mcp_tools.py`)

`create_mcp_tools(...)` define hoy explícitamente:

- `search_properties(query: str)`
- `property_details(property_ref: str)`
- `check_agent_availability(agent_id: str, date: str)`
- `schedule_visit(property_id, agent_id, date, time)`

El resto (`property_interest`, `search_contact`, `create_contact`, `create_demand`, `cancel_visit`) se construye vía **Tool Registry** / factory desde acciones MCP (`tool_factory.py`, `agent_executor_service.py`).

## Semillas y prompts del subgraph comprador

- Lista de tools del agente comprador: `agents/management/commands/seed_buyer_agent.py` (incluye `property_interest`, `cancel_visit`, etc.).
- Reglas operativas detalladas (ordinal → `property_interest`, externalId para demandas, etc.): `agents/buyer_subgraph/prompts/contextual_prompt.py`.

## Mapeo legacy → registry (extracto)

En `agents/services/agent_executor_service.py`, `tool_name_mapping` incluye entre otros:

- `search_property` → `search_properties`
- `check_availability` → `check_agent_availability`
- `register_demand` → `create_demand`

Este ejemplo KISS documenta los **nombres que debe usar el prompt del asistente** alineados con lo que vería el modelo cuando las herramientas están registradas con el nombre de la función (`check_agent_availability`, no la clave del manifest).

## Paridad con la carpeta `rkiglesias` (KISS)

- La lógica de negocio del SaaS **no** se copia en Python dentro de KISS; las tools reales llegan por **MCP** (`tools.md`).
- `input/url_publica.py` solo refleja reglas de presentación (teléfono dígitos, URL `/propiedades/`) ejecutables en el host vía bash (Anthropic) o como contexto para el modelo.
- **`input/saas_property_search_tools.json`**: espejo literal de `name`, `display_name`, `description`, `input_schema` y `output_schema` de las 9 acciones en `mcp_providers/property_search/actions/*.py`, alineado con lo que muestra Agent Studio como tools **External** (mismos textos que en el código del backend).
- Ejecución local sin tocar el runtime KISS: **`run_rk.py`** + **`server/kiss_tool_gateway.py`** en esta carpeta (`CONEXION.md`).
