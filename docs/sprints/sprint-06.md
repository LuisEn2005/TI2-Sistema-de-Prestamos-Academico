# Sprint 6 — Calendario, trazabilidad y cierre integral

## Estado

El Sprint 6 está **terminado**. Este incremento consolida reservas, préstamos,
inventario, calendario institucional y políticas en un flujo único, sencillo y
auditable. El resultado mantiene la separación Astro–Flask y funciona con SQLite
y PostgreSQL mediante SQLAlchemy y Alembic.

## Funcionalidades entregadas

| Módulo | Backend Flask / SQLAlchemy | Frontend Astro |
| --- | --- | --- |
| Reservas | Rangos futuros, solicitudes concurrentes, decisión manual, retiro, rechazo, cancelación, expiración y conversión en préstamo. | Formulario acotado a 90 días, acciones según estado e historial del recorrido. |
| Disponibilidad | Estado efectivo por ítem y fecha, sin convertir `RESERVADO` en un estado físico. | Calendario público sin datos personales e inventario protegido con usuario, rango y solicitudes pendientes. |
| Políticas | Cupo y sanción por rol; plazo y tipos permitidos por rol y modalidad. | Configuración separada y legible para cada regla. |
| Cierres | Feriados, huelgas y otros cierres; reprogramación ordenada de vencimientos y reservas. | Gestión exclusiva del administrador y fechas institucionales visibles. |
| Trazabilidad | Eventos de reserva y aplazamientos de préstamo con actor, fecha, motivo y referencia. | Historial accesible al titular y al personal autorizado. |

## Reglas finales

- Los plazos son días calendario: *in situ* dura 1 día para todos; externo dura
  7 días para estudiantes y 14 para docentes o administrativos. Inicio y fin
  deben ser laborables.
- Una reserva solo puede comenzar desde el siguiente día laborable y como máximo
  90 días en el futuro. Toda reserva no recogida expira al terminar su día inicial.
- Préstamos activos y reservas `PENDIENTE` o `CONFIRMADA` consumen un mismo cupo:
  3 para estudiantes y 5 para docentes o administrativos por defecto.
- El mismo usuario no puede solicitar el mismo recurso en rangos superpuestos.
  Los rangos adyacentes sí son válidos. Solicitudes de usuarios distintos pueden
  competir hasta que el gestor confirme una.
- El gestor prioriza manualmente considerando perfil y fecha de solicitud. Al
  confirmar una reserva, las solicitudes incompatibles quedan rechazadas con un
  motivo auditable.
- `RETIRADA` corresponde al desistimiento de una solicitud pendiente por su
  titular; `RECHAZADA` es la decisión sobre una solicitud; `CANCELADA` se usa
  después de que una reserva fue confirmada.
- No hay renovación de préstamos. Esta decisión evita extensiones indefinidas y
  mantiene la disponibilidad futura bajo el flujo de reservas.
- No existe reutilización física el mismo día: después de una devolución, el
  recurso puede volver a entregarse desde el siguiente día laborable.
- Un cierre institucional mueve vencimientos y reservas al siguiente rango
  laborable. Los cambios aplicados no se revierten automáticamente al desactivar
  el cierre, porque las nuevas fechas ya fueron comunicadas.

## Persistencia

La migración `0015_politicas_y_trazabilidad`:

- crea `politicas_rol` para el cupo y el factor de sanción compartidos;
- conserva en `politicas_servicio` únicamente la combinación rol–modalidad, el
  plazo y la relación normalizada con tipos de recurso;
- elimina de `prestamos` los campos de renovación y el acumulado redundante de
  aplazamientos;
- agrega `eventos_reserva` y `aplazamientos_prestamo`;
- incorpora el estado `RETIRADA` y una restricción contra solicitudes activas
  exactamente duplicadas.

`prestamos.dias_plazo` sigue siendo histórico: conserva el plazo concedido aunque
la política se modifique después. La disponibilidad `RESERVADO` se calcula con
`JOIN` por fecha y nunca se persiste como estado físico del ítem.

## Automatización y calidad

El comando `flask expirar-reservas` debe ejecutarse diariamente a las 00:01 en la
zona `America/Lima`; el arranque de Flask también realiza una recuperación por si
la tarea programada no se ejecutó.

La validación final incluye 138 pruebas de backend con SQLite, la integración de
PostgreSQL en CI, compilación y comprobación de Astro, y siete recorridos
Playwright. Los datos de demostración viven en bases aisladas; la instalación
final usa `DATOS_DEMO=0` y permite crear usuarios, recursos y operaciones desde
una base limpia.

## Resultado del proyecto

El Sprint 6 cierra los recorridos definidos: catálogo público, autenticación por
rol, administración de usuarios e inventario, reserva, decisión manual, entrega,
devolución, sanción, configuración de políticas, cierres e historial operativo.
El detalle global de aceptación está en el [plan de sprints](plan.md).
