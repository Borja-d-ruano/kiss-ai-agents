# Criterios de cierre (tarea conversacional)

Marca la conversación como resuelta cuando:

- el usuario ha quedado satisfecho con información o búsqueda, o
- la visita ha quedado confirmada con éxito de `schedule_visit`, o
- el usuario cancela explícitamente la intención.

No marques cierre si dependías de una herramienta que falló y el usuario aún espera una acción concreta.
