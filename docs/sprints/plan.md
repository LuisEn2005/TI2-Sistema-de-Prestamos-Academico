# Plan de desarrollo por sprints

## Estado general

Los seis sprints están **terminados**. El plan conserva el orden en que creció el
sistema y señala una decisión final importante: RF12, renovación de préstamos,
fue descartado para evitar extensiones indefinidas. Esta decisión no elimina el
historial ni la reserva posterior; obliga a cerrar el préstamo y volver a pasar
por las reglas de disponibilidad y prioridad.

## Sprint 1 — MVP de préstamo y devolución

- **Objetivo:** comprobar la idea central con el menor flujo útil.
- **Backend:** catálogo pequeño, usuarios ficticios, préstamo y devolución de un
  recurso, persistencia SQLite.
- **Frontend:** consulta y formulario mínimo de préstamo/devolución.
- **Resultado:** prototipo funcional documentado en [Sprint 1](sprint-01.md).

## Sprint 2 — Identidad e inventario

- **Objetivo:** reemplazar los datos rígidos por administración real.
- **Backend:** autenticación, sesiones, perfiles, matrícula/vinculación, permisos,
  inventario tipado, migraciones y compatibilidad PostgreSQL.
- **Frontend:** login, gestión de usuarios, catálogo filtrable e inventario.
- **Resultado:** RF01, RF03, RF04 y RF06; base de RF02 y RF05. Véase
  [Sprint 2](sprint-02.md).

## Sprint 3 — Préstamos completos

- **Objetivo:** completar entrega y devolución bajo políticas.
- **Backend:** modalidades, varios ítems, plazos, cupos, tipos permitidos,
  devolución por condición y transacciones atómicas.
- **Frontend:** selección de prestatario, modalidad, días válidos y recepción.
- **Resultado:** RF10, RF11 y reglas principales de RF13. Véase
  [Sprint 3](sprint-03.md).

## Sprint 4 — Reservas

- **Objetivo:** solicitar uso futuro y convertir una reserva en préstamo.
- **Backend:** solicitud, confirmación, rechazo, retiro, cancelación, expiración y
  conversión con referencia al préstamo resultante.
- **Frontend:** rango, seguimiento, decisión manual e historial.
- **Resultado:** RF05 y RF07–RF09. La renovación inicialmente explorada se
  descartó y su endpoint ya no existe. Véase [Sprint 4](sprint-04.md).

## Sprint 5 — Sanciones y configuración

- **Objetivo:** aplicar elegibilidad real y mover reglas fuera del código.
- **Backend:** sanciones por atraso, daño o pérdida; cierre; políticas editables;
  separación entre operación del gestor y configuración del administrador.
- **Frontend:** panel de sanciones y configuración de políticas.
- **Resultado:** RF02, RF13–RF16 y RF18. Véase [Sprint 5](sprint-05.md).

## Sprint 6 — Calendario, trazabilidad y cierre integral

- **Objetivo:** resolver disponibilidad por fecha, cierres institucionales e
  historial, y validar el producto completo.
- **Backend:** rangos hasta 90 días, competencia manual, cupo compartido,
  inventario por fecha, feriados/huelgas, reprogramación, eventos de reserva,
  aplazamientos y expiración programada.
- **Frontend:** calendario público, inventario protegido por fecha, acciones por
  estado y consulta de historial.
- **Resultado:** RF17 y cierre conjunto de requisitos funcionales y no
  funcionales. Véase [Sprint 6](sprint-06.md).

## Matriz final de requisitos

| Requisito | Resultado | Sprint de cierre |
| --- | --- | ---: |
| RF01 | Usuarios, perfiles y vigencias administrables. | 2 |
| RF02 | Elegibilidad por vigencia y sanciones activas. | 5 |
| RF03 | Política por rol y modalidad. | 3 |
| RF04 | Inventario tipado y extensible. | 2 |
| RF05 | Estado físico y disponibilidad derivada por fecha. | 6 |
| RF06 | Catálogo, filtros y calendario público. | 6 |
| RF07 | Solicitud futura y decisión manual. | 6 |
| RF08 | Retiro, rechazo, cancelación y expiración. | 6 |
| RF09 | Reserva confirmada convertida en préstamo. | 4 |
| RF10 | Entrega con plazo y política aplicados. | 3 |
| RF11 | Devolución con condición. | 3 |
| RF12 | Descartado por decisión funcional; no hay renovación. | 6 |
| RF13 | Bloqueo por sanción, cupo compartido y disponibilidad. | 6 |
| RF14 | Sanción automática por atraso. | 5 |
| RF15 | Sanción manual por daño o pérdida. | 5 |
| RF16 | Cierre de sanciones. | 5 |
| RF17 | Historial de operaciones y eventos relevantes. | 6 |
| RF18 | Configuración administrativa persistente. | 5 |

## Criterios de entrega

El producto se considera completo cuando los recorridos operan de extremo a
extremo, las restricciones se aplican también en base de datos, las respuestas
públicas no exponen datos personales y la misma migración funciona en SQLite y
PostgreSQL. La CI ejecuta pruebas de backend, integración PostgreSQL, build de
Astro y Playwright.

La demostración usa una base aislada con datos ficticios. La entrega final debe
arrancar con `DATOS_DEMO=0`, una base nueva y las credenciales del administrador
inicial en variables de entorno; desde allí se crean usuarios y recursos reales.
Las incidencias concretas de Jira se administran fuera de este documento.
