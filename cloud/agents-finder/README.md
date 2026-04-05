# agents-finder

UI estática (sin frameworks) + `server.py` (stdlib) que expone:

- `GET /` — página
- `GET /api/list?path=` — listado (path relativo a la raíz de agentes)
- `GET /api/raw?path=` — lectura de fichero (texto, límite 2 MB)
- `PUT /api/raw?path=` — subida / sobrescritura

Por defecto la raíz es `local/examples` respecto al repo (o `KISS_AGENTS_ROOT`).
