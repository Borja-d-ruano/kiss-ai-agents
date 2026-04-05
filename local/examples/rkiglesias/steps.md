# Pasos de referencia (no sustituyen a `prompt.md`)

1. Inmueble: `search_properties` / `property_details` / `property_interest` (vía MCP en `tools.md`).
2. Información y URL corregida según `data.md` (o `input/url_publica.py` si validas con bash).
3. Si hay interés real: nombre + teléfono en este chat → `search_contact` / `create_contact`.
4. Cualificación mínima (venta si aplica + cuándo comprar).
5. `create_demand` con observaciones reales.
6. Si `visit_requested`: `check_agent_availability` y/o `schedule_visit`; `cancel_visit` solo si procede.

**Sin MCP:** solo conversación + helpers locales (`input/`); no registrar en CRM ni buscar propiedades reales.
