# agents-finder

UI estática (sin frameworks) + `server.py` (stdlib) que expone:

- `GET /` — página
- `GET /api/list?path=` — listado (path relativo a la raíz de agentes)
- `GET /api/raw?path=` — lectura de fichero (texto, límite 2 MB)
- `PUT /api/raw?path=` — subida / sobrescritura

Por defecto la raíz es `local/examples` respecto al repo (o `KISS_AGENTS_ROOT`).

Si el puerto **9393** está ocupado (p. ej. otro `server.py` en marcha), sin `AGENTS_FINDER_PORT` el proceso prueba **9394–9402** automáticamente. Con `AGENTS_FINDER_PORT` fijado, falla con un mensaje que indica `lsof` y cambiar de puerto.
