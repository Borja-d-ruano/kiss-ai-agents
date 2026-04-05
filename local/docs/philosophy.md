# Filosofía KISS Agents (reglas no negociables)

Sintetizado desde [`../../../../analisis-docs/KISS_agents-analisis-y-propuesta.md`](../../../../analisis-docs/KISS_agents-analisis-y-propuesta.md). Si el código contradice esto, gana el documento.

## Lo que NO hacemos

| Regla | Motivo |
|-------|--------|
| Sin BBDD para orquestar agentes | El filesystem (carpeta del agente) es el estado. |
| Sin librerías de agentes / scheduling | LangChain, APScheduler, Bull, etc. añaden abstracción y mantenimiento. |
| Sin heartbeats ni daemons de polling | El reloj es **cron** (o `curl` periódico), no un proceso residente preguntando. |
| Sin “procesar negocio” en nuestro código | No NLP, clasificación ni extracción en el backend; eso lo hace el modelo. |
| Menos de ~1000 líneas de software ejecutable | Si crece más, recortar o justificar con ADR. |

## Lo que SÍ hacemos

1. **Enviar markdown al modelo** (contexto = contenidos de la carpeta).
2. **Recibir markdown del modelo** (respuesta estructurada con `writes` a archivos).

El backend es un **cartero** de `.md`.

## Principios operativos

- Un agente = una carpeta con `.md` (+ `input/`, `output/`). El wiring máquina-legible de MCP va en bloque JSON dentro de `tools.md`.
- Markdown = control-plane (`prompt.md`, `tools.md`, `schedule.md`, `memory.md`, `steps.md`, `done.md`).
- El modelo = runtime de razonamiento (en prod: API real; en demo: stub).
- Scheduling = `schedule.md` + comparación trivial de cron + disparador externo.

## Extensiones del runtime (agnósticas del negocio)

Siguiendo [KISS_agents-analisis-y-propuesta.md](../../../../analisis-docs/KISS_agents-analisis-y-propuesta.md): el producto sigue siendo **cartero de markdown**; el modelo es el runtime inteligente. Lo que sí puede crecer **sin** meter lógica de dominio en Python propio:

1. **Llamadas HTTP genéricas a tools**  
   Un único bucle “modelo ↔ herramientas” donde cada tool es **solo transporte**: `POST` (o `GET`) a una URL base tomada de **entorno** + path fijo declarado en **`tools.md`** (JSON), cuerpo = argumentos JSON del modelo, respuesta = texto/JSON devuelto al modelo. Esquemas de parámetros en un fichero bajo **`input/`** de la carpeta del agente (como `saas_property_search_tools.json`).  
   *Prohibido en ese puente:* interpretar lenguaje natural, mapear sinónimos o reglas de negocio; eso lo hace el LLM.  
   *Encaja con rk:* la base puede apuntar a un gateway que hable con iagestión / rag-api; el agente rk puede seguir llevando `run_rk.py` en su carpeta hasta que ese puente exista en el runner genérico.

2. **Ejecución de Python**  
   - **Incluir** `input/*.py` en el contexto (`md_io`) para que el modelo vea el código.  
   - **Ejecutar** código en el **proveedor** (OpenAI Code Interpreter / Shell, Anthropic `code_execution` / bash con `cwd` en la carpeta del agente). KISS no evalúa `exec()` del usuario en el runner por defecto (riesgo y filosofía: no segundo intérprete de negocio en tu proceso).

3. **MCP remoto** (ya previsto en `tools.md`)  
   Misma idea: el conector habla con un servidor externo; tu código solo reenvía. El transporte es HTTP (p. ej. Streamable MCP). Integraciones como **Hopx** que publican MCP por **stdio** (`uvx hopx-mcp`) no encajan directamente con ese `url`: para agentes KISS la fachada HTTP vive fuera del núcleo `runtime/`, en el Worker Cloudflare [`cloud/code-executor-mcp`](../cloud/code-executor-mcp/); detalle en [`mcp-hopx.md`](mcp-hopx.md).

Con esto “cualquier negocio” añade **markdown + JSON de tools + scripts opcionales en `input/`**; el runtime solo añade **primitivas de transporte** acotadas, no reglas de RK ni de otro vertical.
