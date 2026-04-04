# Paridad orientada a resultado: LangChain (ecosistema) vs KISS Agents

LangChain no es un solo producto: incluye **langchain-core**, **langchain**, integraciones en **langchain-community**, **LangGraph**, **LangSmith**, plantillas y docenas de paquetes. Esta tabla compara **el resultado útil** que suele buscarse con ese ecosistema frente a lo que KISS Agents cubre hoy (carpeta + markdown + modelo + tick + adaptadores).

Leyenda: **Cubierto** = lo resuelves con el diseño actual o con el proveedor (OpenAI/Anthropic) sin añadir un framework. **Parcial** = posible con poco código extra o solo en parte. **No** = no es objetivo del runtime mínimo o requeriría módulos nuevos sustanciales.

| Área / feature típica (LangChain y satélites) | KISS Agents hoy | Nota |
|-----------------------------------------------|-----------------|------|
| Orquestar LLM con prompts y contexto | Cubierto | `load_agent` + `call_model`. |
| Bucles tipo “agente hasta terminar” | Cubierto | `run()` multi-turn + `final`. |
| Herramientas (tools) y llamadas | Parcial / Cubierto | Vía API del proveedor (shell, code interpreter, MCP remoto, bash local en Claude); no hay registro genérico de tools propias en Python salvo stub. |
| MCP remoto | Cubierto | `tools.md` (bloque JSON) + adaptadores; Anthropic connector; OpenAI Responses MCP. |
| Ejecución shell / código en sandbox | Cubierto | OpenAI hosted shell / code interpreter; Claude code_execution + bash local. |
| Memoria conversacional estructurada | Parcial | `memory.md` / archivos en carpeta; no hay buffer de mensajes tipado como LC Memory. |
| Memoria vectorial / RAG | No | No embeddings, vector store ni retriever; el modelo + MCP podrían acercarse si montas un MCP de búsqueda. |
| Document loaders (PDF, web, DB, …) | No | No hay loaders; mismo comentario: MCP o code interpreter. |
| Text splitters | No | No aplica al core; el modelo o herramientas externas. |
| Chains lineales (LCEL / Runnable) | Parcial | Sustituido por “carpetas + steps.md + re-ejecución”; sin grafo explícito en código. |
| Routers / branching en código | No | El modelo decide leyendo markdown; sin router programático. |
| AgentExecutor / políticas de agente | Parcial | `max_turns` fijo; sin políticas avanzadas ni stop hooks. |
| Function calling genérico (tus funciones Python) | Parcial | Hoy centrado en tools del proveedor; registry propio sería extensión. |
| Structured output / Pydantic parsers | No | Salida markdown + `writes`; sin validación schema de respuesta. |
| Streaming de tokens | No | `urllib` completo; sin SSE en el runtime local. |
| Callbacks / eventos / verbose | No | Sin sistema de callbacks; logs mínimos. |
| Caché de LLM | No | Opcional en proveedor; no en KISS. |
| Tracing / observabilidad (LangSmith-like) | No | Artefactos en `output/` y `schedule.md` History. |
| LangGraph: grafo con estado | No | Estado = filesystem; sin máquina de estados explícita. |
| LangGraph: persistencia / checkpoint | Parcial | Git + carpetas; sin checkpoint de grafo. |
| LangGraph: human-in-the-loop | No | Manual editando `.md` o siguiente `run`. |
| Multi-agente coordinado | No | Un agente por carpeta; coordinación vía prompts o varias carpetas. |
| SQL agent / agents especializados | No | Podría aproximarse con MCP o bash + cliente SQL. |
| Integraciones SaaS masivas (community) | Parcial | MCP / HTTP / documentación en `tools.md`; no catálogo LC. |
| Despliegue / hosting (LangServe, etc.) | No | HTTP mínimo local; cloud es fase aparte. |
| Evaluación / datasets formales | No | Fuera de alcance KISS. |
| Indexación / vector DB managed | No | Ver RAG. |
| Output parsers (listas, JSON, etc.) | No | |
| RunnableParallel / batching | No | |
| Few-shot en plantillas | Parcial | Texto en `prompt.md` / `agent.md`. |
| Chat history tipado (AIMessage/HumanMessage) | Parcial | Contexto concatenado como texto; no tipos LC. |
| Moderation / guardrails framework | No | Políticas en markdown + modelo. |
| Multimodal (imágenes en input) | Parcial | No en el loader actual de archivos (solo ciertos sufijos); extensible en `md_io`. |
| Assistants API / Threads OpenAI | No | Modelo distinto; KISS usa Responses/Messages según adaptador. |
| Cost tracking / token counting explícito | No | Facturación del proveedor. |

## ¿Cuándo podrías decir “sustituido” (en sentido de resultado)?

Cuando tu objetivo es: **agente con contexto versionable, ejecución con herramientas potentes del modelo, programación por cron y cero framework de orquestación**, KISS ya sustituye la parte “chain + agent executor + integrations glue” de LangChain para muchos casos.

**No** sustituye (sin trabajo adicional) RAG clásico, LangGraph complejo, observabilidad tipo LangSmith, streaming, ni el catálogo entero de integraciones de `langchain-community`.

## Referencia de nombres (ecosistema LC, no exhaustiva)

- **langchain-core**: mensajes, runnables, LCEL.  
- **langchain**: cadenas y agentes clásicos.  
- **langchain-community**: loaders, vector stores, herramientas de terceros.  
- **langchain-text-splitters**: división de texto.  
- **langchain-openai / langchain-anthropic**: wrappers de chat model.  
- **langgraph**: grafos, estado, checkpoints, HITL.  
- **langsmith**: trazas, evaluación, despliegue.
