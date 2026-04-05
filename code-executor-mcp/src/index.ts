import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { createMcpHandler } from "agents/mcp";
import { z } from "zod";
import { executeCodeIsolated } from "./hopx";

function createServer(env: Env) {
  const server = new McpServer({
    name: "code-executor-mcp",
    version: "1.0.0",
  });

  server.tool(
    "execute_code_isolated",
    "Run code in an ephemeral Hopx sandbox (one-shot). Creates a sandbox, executes, deletes. Requires HOPX_API_KEY on the Worker.",
    {
      code: z.string().describe("Source code to run"),
      language: z
        .string()
        .optional()
        .describe("Language: python, javascript, bash, or go (default python)"),
      timeout: z
        .number()
        .int()
        .min(1)
        .max(300)
        .optional()
        .describe("Execution timeout seconds (max 300)"),
      template_name: z
        .string()
        .optional()
        .describe('Hopx template name, default "code-interpreter"'),
      region: z.string().optional().describe("Optional Hopx region"),
      env: z
        .record(z.string(), z.string())
        .optional()
        .describe("Optional env vars for this execution only"),
    },
    async ({ code, language, timeout, template_name, region, env: envVars }) => {
      const out = await executeCodeIsolated(env, {
        code,
        language,
        timeout,
        template_name,
        region: region ?? null,
        env: envVars ?? null,
      });
      return {
        content: [{ type: "text" as const, text: JSON.stringify(out, null, 2) }],
      };
    },
  );

  return server;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const server = createServer(env);
    return createMcpHandler(server)(request, env, ctx);
  },
} satisfies ExportedHandler<Env>;
