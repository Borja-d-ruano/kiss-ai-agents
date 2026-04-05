# Herramientas (canónico para el modelo)

## Modo ejecutable (solo en esta carpeta)

**`run_rk.py`** usa OpenAI Chat Completions y ejecuta cada tool con **`POST {KISS_HTTP_TOOL_BASE_URL}/kiss-tools/<name>`**. Los nombres y parámetros salen de **`input/saas_property_search_tools.json`**. No depende de `KISS_PROVIDER` ni de código extra en `runtime/`.

1. Gateway: `python3 server/kiss_tool_gateway.py` (desde esta carpeta).
2. Variables: ver **`CONEXION.md`** / **`connection.example.env`**. Con **`KISS_SAAS_API_BASE_URL`** (+ token) el gateway llama a la API real del comprador; sin ellas, modo demo.
3. Agente: `python3 run_rk.py "…"`.

El bloque JSON de abajo sigue siendo el canal **MCP** si usas `python main.py run …` con `KISS_PROVIDER=openai|anthropic`.

## Bloque obligatorio (JSON)

`mcp_servers` es la forma **neutral**: el runtime la duplica en listas OpenAI y Anthropic. Mientras esté vacío, las herramientas CRM/propiedades **no** existen para el modelo salvo que uses otro canal.

```json
{
  "openai_mcp_tools": [],
  "anthropic_mcp_servers": [],
  "mcp_servers": []
}
```

### Plantilla (copiar dentro de `mcp_servers` cuando tengas URL)

Sustituye `NOMBRE` y `URL` por los del tenant. El `type` suele ser `mcp` (OpenAI) y se reutiliza en el mapeo.

**Hopx (ejecución aislada):** despliega el Worker en `cloud/code-executor-mcp`, pon `HOPX_API_KEY` con Wrangler y usa la URL pública del Worker (no la API key en markdown). Ejemplo comentado:

```json
[
  {
    "name": "hopx",
    "url": "https://TU-CUENTA.code-executor-mcp.workers.dev/mcp",
    "type": "mcp"
  }
]
```

Documentación: [`../../docs/mcp-hopx.md`](../../docs/mcp-hopx.md).

```json
[
  {
    "name": "NOMBRE_SERVIDOR_MCP",
    "url": "https://tu-servidor-mcp.example/mcp",
    "type": "mcp"
  }
]
```

También puedes rellenar solo `openai_mcp_tools` o solo `anthropic_mcp_servers` si el despliegue es de un solo proveedor; ver [`../../docs/adapters.md`](../../docs/adapters.md).

## Espejo de las tools “External” del SaaS (Agent Studio)

En la plataforma (`saas-platform-rk-all-fresh`), el agente comprador seed (`seed_buyer_agent.py`) enlaza **9** acciones MCP del proveedor **`property_search`**. En Agent Studio aparecen como **External** con títulos en inglés; el nombre técnico que debe usar el modelo es el `name` en **snake_case**.

**Registro canónico (display, descripción UI, `input_schema` / `output_schema` copiados del código Python):**  
→ [`input/saas_property_search_tools.json`](input/saas_property_search_tools.json)  
Ese fichero se carga en el contexto del run junto al resto de `input/`.

| # | Nombre invocable (`name`) | Título en UI (display_name) | Descripción en SaaS (`description`) |
|---|---------------------------|----------------------------|-------------------------------------|
| 1 | `search_properties` | Search Properties | Search for properties using configurable filters |
| 2 | `property_details` | Property Details | Get detailed information about a specific property by ID |
| 3 | `property_interest` | Property Interest | Handle user interest in a specific property from search results |
| 4 | `search_contact` | Search Contact | Search for contacts by phone number in iagestión |
| 5 | `create_contact` | Create Contact | Create a new contact in iagestión with name, phone, and/or email |
| 6 | `create_demand` | Create Demand | Create a new demand in iagestión for a property with contact information |
| 7 | `check_agent_availability` | Check Agent Availability | Check agent availability for a specific date |
| 8 | `schedule_visit` | Schedule Visit | Schedule a visit with an agent for a specific property |
| 9 | `cancel_visit` | Cancel Visit | Cancel or delete a scheduled visit by gestion ID |

**Nota:** Si en un tenant añades otra tool en el modal (p. ej. **context7** u otra integración), no está en `BUYER_TOOL_NAMES` del seed; trátala como catálogo adicional configurado en ese entorno.

### Uso para el modelo

- Invoca solo por **`name`** exacto de la tabla anterior.
- Argumentos y tipos: **`input/saas_property_search_tools.json`** (misma forma que persisten las `MCPAction` en Django).
- Reglas de negocio y tono: **`prompt.md`** (no sustituyen al esquema).

### Detalle de implementación en el repo SaaS

Clases `BaseAction` bajo `mcp_providers/property_search/actions/`:

`search_action.py` (SearchProperties), `property_details_action.py`, `property_interest_action.py`, `search_contact_action.py`, `create_contact_action.py`, `create_demand_action.py`, `check_agent_availability_action.py`, `schedule_visit_action.py`, `cancel_visit_action.py`.
