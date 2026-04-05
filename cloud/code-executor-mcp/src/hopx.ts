const DEFAULT_API_BASE = "https://api.hopx.dev";

function apiBase(env: Env): string {
  return (env.HOPX_BASE_URL?.trim() || DEFAULT_API_BASE).replace(/\/$/, "");
}

function joinUrl(base: string, path: string): string {
  const b = base.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${b}${p}`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function hopxApi(env: Env, path: string, init?: RequestInit): Promise<Response> {
  const url = joinUrl(apiBase(env), path);
  const headers = new Headers(init?.headers);
  headers.set("X-API-Key", env.HOPX_API_KEY);
  if (init?.body != null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(url, { ...init, headers });
}

async function readJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { raw: text };
  }
}

export type ExecuteIsolatedInput = {
  code: string;
  language?: string;
  timeout?: number;
  template_name?: string;
  region?: string | null;
  env?: Record<string, string> | null;
};

export async function executeCodeIsolated(env: Env, input: ExecuteIsolatedInput): Promise<unknown> {
  if (!env.HOPX_API_KEY?.trim()) {
    return { error: "HOPX_API_KEY is not set on the Worker (use wrangler secret put HOPX_API_KEY)" };
  }

  const language = (input.language ?? "python").trim().toLowerCase() || "python";
  const execTimeout = Math.min(Math.max(input.timeout ?? 120, 1), 300);
  const templateName = input.template_name ?? "code-interpreter";

  const createBody: Record<string, unknown> = {
    template_name: templateName,
    timeout_seconds: 600,
    internet_access: true,
  };
  if (input.region) createBody.region = input.region;

  const createRes = await hopxApi(env, "/v1/sandboxes", {
    method: "POST",
    body: JSON.stringify(createBody),
  });
  const createJson = (await readJson(createRes)) as Record<string, unknown>;
  if (!createRes.ok) {
    return {
      error: "Failed to create sandbox",
      status: createRes.status,
      details: createJson,
    };
  }

  const sandboxId = String(createJson.id ?? "");
  const authToken = String(createJson.auth_token ?? "");
  if (!sandboxId || !authToken) {
    return { error: "Create sandbox response missing id or auth_token", details: createJson };
  }

  let publicHost = String(createJson.public_host ?? createJson.direct_url ?? "").trim();

  if (!publicHost || createJson.status !== "running") {
    for (let i = 0; i < 90; i++) {
      const gr = await hopxApi(env, `/v1/sandboxes/${sandboxId}`);
      const gj = (await readJson(gr)) as Record<string, unknown>;
      if (!gr.ok) {
        await hopxApi(env, `/v1/sandboxes/${sandboxId}`, { method: "DELETE" }).catch(() => {});
        return { error: "Failed to get sandbox", status: gr.status, details: gj };
      }
      publicHost = String(gj.public_host ?? gj.direct_url ?? "").trim();
      if (publicHost && gj.status === "running") break;
      await sleep(1000);
    }
  }

  if (!publicHost) {
    await hopxApi(env, `/v1/sandboxes/${sandboxId}`, { method: "DELETE" }).catch(() => {});
    return { error: "Sandbox has no public_host yet", sandbox_id: sandboxId };
  }

  const agentRoot = publicHost.replace(/\/$/, "");

  for (let i = 0; i < 60; i++) {
    const hr = await fetch(joinUrl(agentRoot, "/health"), {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    if (hr.ok) {
      try {
        const hj = (await hr.json()) as { status?: string };
        if (hj.status === "healthy") break;
      } catch {
        break;
      }
    }
    await sleep(1000);
  }

  const execPayload: Record<string, unknown> = {
    language,
    code: input.code,
    workdir: "/workspace",
    timeout: execTimeout,
  };
  if (input.env && Object.keys(input.env).length > 0) {
    execPayload.env = input.env;
  }

  const execRes = await fetch(joinUrl(agentRoot, "/execute"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(execPayload),
  });

  const execJson = (await readJson(execRes)) as Record<string, unknown>;
  let result: Record<string, unknown>;

  if (!execRes.ok) {
    result = {
      error: "Execute failed",
      http_status: execRes.status,
      sandbox_id: sandboxId,
      details: execJson,
    };
  } else {
    result = {
      stdout: execJson.stdout ?? "",
      stderr: execJson.stderr ?? "",
      exit_code: execJson.exit_code ?? 0,
      execution_time: execJson.execution_time ?? 0,
      success: execJson.success ?? true,
      sandbox_id: sandboxId,
      mode: "isolated",
    };
    if (execJson.rich_outputs) {
      result.rich_outputs = execJson.rich_outputs;
    }
  }

  await hopxApi(env, `/v1/sandboxes/${sandboxId}`, { method: "DELETE" }).catch(() => {});

  return result;
}
