# Carpeta compartida (`local/shared`)

Aquí puedes guardar **ficheros JSON de configuración de herramientas** (MCP, listas de servidores, etc.) que quieras **reutilizar en varios agentes** sin copiar el mismo contenido en cada carpeta y **sin usar symlinks**.

---

## Para quien no programa

- Piensa en esta carpeta como un **cajón común** del proyecto: un único sitio donde vive la “lista de conexiones a herramientas externas”.
- Cada **agente** sigue teniendo su propia carpeta (por ejemplo bajo `local/examples/…`). En el fichero **`tools.md`** de ese agente se **indica el nombre** del JSON compartido; el sistema lo carga desde aquí.
- **No hace falta** duplicar URLs ni listas largas en cada agente: las cambias **una vez** en `local/shared/` y todos los agentes que apunten a ese fichero verán la versión nueva en la siguiente ejecución.
- **Importante:** no pongas **contraseñas ni API keys** dentro de estos JSON. Las claves van en **variables de entorno** (como en el resto del proyecto). Aquí solo URLs públicas y nombres de servidores, igual que en `tools.md`.

---

## Para desarrolladores

### Convención `@shared/`

En el primer bloque ` ```json ` de **`tools.md`** del agente:

```json
{
  "include": "@shared/mi-pack-mcp.json",
  "mcp_servers": []
}
```

o varios:

```json
{
  "includes": ["@shared/base.json", "input/agent-only.json"],
  "openai_mcp_tools": [],
  "anthropic_mcp_servers": []
}
```

- **`@shared/ruta.json`** se resuelve a **`local/shared/ruta.json`** (relativo al árbol `local/`, junto a `runtime/`).
- No se permiten `..` en la parte tras `@shared/`. Solo ficheros **`.json`** existentes.
- Misma semántica que los includes normales: solo se fusionan **`mcp_servers`**, **`openai_mcp_tools`** y **`anthropic_mcp_servers`** desde los JSON encadenados; profundidad máxima **5**; deduplicación por `name` + `url` / `server_url`. Las claves como **`anthropic_skills`** van en el **raíz** de `tools.md`, no en los packs compartidos (salvo que quieras que un JSON compartido solo aporte listas MCP).

### Variable de entorno

| Variable | Uso |
|----------|-----|
| `KISS_SHARED_TOOLS` | (Opcional) Ruta absoluta a otra carpeta que actúe como raíz del prefijo `@shared/` (por defecto: esta carpeta `local/shared`). |

### Documentación ampliada

- [`../docs/adapters.md`](../docs/adapters.md) — pipeline `tools.md`, includes y MCP.
- Tutoriales §**14.5.1** (ES/EN en [`../../docs/`](../../docs/)) — mismo comportamiento descrito para usuarios y sistemas.

### Ejemplo mínimo

1. Crea `local/shared/equipo-crm.json`:

```json
{
  "mcp_servers": [
    { "name": "crm_demo", "url": "https://ejemplo.example/mcp", "type": "mcp" }
  ]
}
```

2. En `tools.md` del agente:

```json
{
  "include": "@shared/equipo-crm.json",
  "mcp_servers": []
}
```

3. Ejecuta `main.py run` como siempre; `resolve_tools_config` cargará el pack compartido.
