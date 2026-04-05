# Datos de negocio

| Clave | Valor actual (tenant RK) |
| --- | --- |
| `CRM_NOMBRE_USUARIO` | Nombre amigable del CRM (ej. "IA Gestión") para notas internas; **no** lo menciones al usuario final (ver `prompt.md`). |
| `BASE_URL_COMPRADORES` | Sitio público compradores: **`https://rkcompradores.alt-94.dev`** (sin barra final). Coincide con el portal [RK compradores](https://rkcompradores.alt-94.dev/). |

Otras tools o el gateway demo pueden leer la misma base desde env **`KISS_RK_PUBLIC_BASE`** (ver `CONEXION.md`).

## Regla de URLs públicas

Si una URL de propiedad contiene el segmento `/properties/`, al mostrarla al usuario debe sustituirse **solo** ese segmento por `/propiedades/` (sobre `BASE_URL_COMPRADORES` o las que devuelvan las herramientas).

Ejemplo:

- Recibido: `https://rkcompradores.alt-94.dev/properties/3331`
- Mostrar: `https://rkcompradores.alt-94.dev/propiedades/3331`

Cuando muestres una URL: `Ver propiedad: <url_corregida>`.

## Runtime

### Tools ejecutables (todo en esta carpeta)

`python3 run_rk.py` + gateway `server/kiss_tool_gateway.py`. Variables: [`CONEXION.md`](CONEXION.md), [`connection.example.env`](connection.example.env).

### Runner genérico KISS (`python main.py run …` desde `local/runtime`)

| Variable | Uso |
| --- | --- |
| `KISS_PROVIDER` | `stub`, `openai` o `anthropic`. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Credenciales del proveedor. |
| `KISS_BASH_CWD` | Opcional; cwd de `bash` (Anthropic). |
| `KISS_OPENAI_ENABLE_CODE_INTERPRETER` | `1` opcional (OpenAI Responses). |

Lógica reutilizable **en el host** (misma regla de teléfonos y URLs): `input/url_publica.py` + notas en `input/KISS_RUNTIME.md`.
