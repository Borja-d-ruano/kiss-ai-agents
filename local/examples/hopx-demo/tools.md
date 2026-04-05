# Herramientas

Sustituye la URL por la de tu Worker desplegado (`npx wrangler deploy` en `cloud/code-executor-mcp/`). La API key de Hopx va solo en el Worker (`wrangler secret put HOPX_API_KEY`), no aquí.

```json
{
  "openai_mcp_tools": [],
  "anthropic_mcp_servers": [],
  "mcp_servers": [
    {
      "name": "hopx",
      "url": "https://code-executor-mcp.alt94studio.workers.dev/mcp",
      "type": "mcp"
    }
  ]
}
```

Más contexto: [`../../docs/mcp-hopx.md`](../../docs/mcp-hopx.md).
