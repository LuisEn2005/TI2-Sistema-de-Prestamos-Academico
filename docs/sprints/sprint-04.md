# Sprint 4 — Reservas

## Objetivo y estado

El Sprint 4 está **terminado**. Introdujo el ciclo de reservas sobre el catálogo:
solicitud, confirmación manual, cancelación, expiración y conversión en préstamo.
Las reglas de calendario, competencia y trazabilidad fueron consolidadas después
en el Sprint 6.

## Alcance funcional

| Requisito | Resultado |
| --- | --- |
| RF05 | La reserva no modifica el estado físico del ítem; su disponibilidad se calcula por fecha. |
| RF07 | Un usuario habilitado solicita un recurso bajo un rol, modalidad y rango. |
| RF08 | El ciclo distingue retiro, rechazo, cancelación y expiración. |
| RF09 | Una reserva confirmada se convierte en préstamo al registrar la entrega física. |
| RF12 | Descartado posteriormente: el sistema final no permite renovaciones. |

## Flujo vigente

1. El usuario selecciona recurso, perfil, modalidad y rango futuro.
2. La API valida habilitación, tipos permitidos, cupo, días laborables y conflictos.
3. La solicitud queda `PENDIENTE`; otras personas pueden competir por el mismo rango.
4. El gestor confirma una solicitud o la rechaza con un motivo.
5. En la fecha inicial, el gestor registra la entrega y la reserva queda
   `CONVERTIDA`, vinculada al préstamo creado.
6. Si no se recoge, expira al terminar el día inicial.

Los estados finales son `PENDIENTE`, `CONFIRMADA`, `RETIRADA`, `RECHAZADA`,
`CANCELADA`, `EXPIRADA` y `CONVERTIDA`. El listado normal muestra solo estados
activos; el filtro de historial incluye los estados terminales y su bitácora.

## Decisiones posteriores que sustituyen el diseño inicial

La primera versión del sprint contenía una acción de renovación y trataba
`RESERVADO` como estado persistido. Las pruebas del equipo mostraron que ambas
decisiones generaban ambigüedad. El sistema final:

- no renueva préstamos;
- conserva únicamente estados físicos en `items`;
- deriva la disponibilidad reservada según la fecha;
- permite retirar una solicitud pendiente y cancelar únicamente una confirmada;
- registra cada transición con actor y fecha.

Esta sección preserva la evolución del sprint sin presentar reglas obsoletas como
funcionalidad actual.

## Calidad

Las pruebas de dominio, API y navegador cubren solicitud, decisión manual,
conversión, expiración, visibilidad por rol y ausencia del endpoint de renovación.
El detalle de las reglas consolidadas está en [Sprint 6](sprint-06.md).
