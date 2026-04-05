# code-executor-mcp

Cloudflare Worker: servidor MCP remoto (Streamable HTTP en `/mcp`) que expone `execute_code_isolated` y llama a la [API Hopx](https://docs.hopx.ai) con `fetch`. No incluyas `HOPX_API_KEY` en el repo.

## Desarrollo local

```bash
cd "KISS Agents/cloud/code-executor-mcp"
npm install
cp .dev.vars.example .dev.vars   # rellena HOPX_API_KEY
npm start
```

El endpoint MCP suele ser `http://localhost:8788/mcp` (puerto según Wrangler).

## Producción

```bash
npx wrangler secret put HOPX_API_KEY
# opcional: vars en dashboard o wrangler para HOPX_BASE_URL (staging)
npx wrangler deploy
```

Pon la URL `https://<worker>/mcp` en `mcp_servers` del `tools.md` del agente. Guía KISS: `local/docs/mcp-hopx.md`.

## Seguridad

La plantilla es **sin autenticación** en el propio MCP: cualquiera con la URL puede invocar herramientas. Para uso real, añade [autenticación Cloudflare](https://developers.cloudflare.com/agents/guides/remote-mcp-server/#add-authentication).
