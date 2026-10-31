# Sprint 6 — Calendario, disponibilidad y cierre integral

## Estado del incremento

El Sprint 6 está **en progreso**. Este primer incremento termina la planificación
por fechas y los días no laborables. La auditoría transversal y el historial
filtrable siguen pendientes; por ello el sprint y el proyecto todavía no se
declaran cerrados.

## Funcionalidad implementada

| Módulo | Backend Flask / SQLAlchemy | Frontend Astro |
| --- | --- | --- |
| Reservas | Solicitud por modalidad y rango, varias solicitudes pendientes, confirmación o rechazo manual y expiración al final del día inicial. | Selección de fechas, estados y acciones simples para confirmar, rechazar o entregar. |
| Disponibilidad | Cálculo diario `DISPONIBLE`, `RESERVADO` o `NO_DISPONIBLE`; no expone datos personales en la ruta pública. | Calendario mensual en el catálogo y calendario de gestión con solicitante, perfil y fecha de registro. |
| Cupos | Préstamos activos y reservas pendientes o confirmadas consumen el mismo límite de la política. | El formulario muestra préstamos, reservas y cupo restante. |
| Días laborables | Sábados, domingos y cierres impiden entrega y devolución; las fechas inválidas incluyen una sugerencia. | Fechas de inicio y fin visibles y limitadas por la política seleccionada. |
| Cierres | Feriados, huelgas u otros periodos aplazan préstamos y desplazan reservas confirmadas al siguiente rango libre. | El administrador registra, edita, activa o desactiva periodos desde Configuración. |

## Reglas acordadas

- El préstamo *in situ* termina el mismo día para todos los perfiles.
- El préstamo externo admite hasta 7 días para estudiantes y 14 para docentes o
  administrativos. Son días calendario; inicio y fin deben ser laborables.
- La disponibilidad reservada es temporal y se calcula por fecha. Una solicitud
  pendiente no cambia el estado físico del recurso.
- El gestor decide manualmente qué solicitud confirmar. Al confirmar una, las
  pendientes incompatibles quedan rechazadas con un motivo.
- No existe rotación el mismo día: un rango nuevo empieza después de la fecha final
  del compromiso anterior.
- Los cierres ya aplicados no se revierten al desactivarlos, para no cambiar fechas
  que ya fueron comunicadas.

## Persistencia y API

La migración `0014_calendario_y_rangos` amplía `reservas`, añade
`dias_aplazados` a `prestamos`, crea `dias_no_laborables`, elimina la exclusividad
de solicitudes pendientes y actualiza a 14 días las políticas externas del
personal que conservaban el valor inicial de 15.

Las rutas principales añadidas son:

- `GET /api/calendario/hoy`, fecha institucional usada por los formularios;
- `GET /api/items/{id}/calendario`, pública y sin datos del solicitante;
- `GET /api/reservas/calendario`, protegida para el personal de gestión;
- `POST /api/reservas/{id}/rechazo`;
- `GET`, `POST` y `PATCH /api/dias-no-laborables`.

## Calidad y trabajo pendiente

Las pruebas cubren solicitudes en competencia, privacidad del calendario, cupo
compartido, política de 14 días, fines de semana, reprogramación, permisos y
edición de cierres. La CI mantiene SQLite, PostgreSQL, build de Astro y recorridos
Playwright con una base aislada.

Para terminar el Sprint 6 falta implementar RF17: bitácora e historial integral
por usuario e ítem, sus filtros en la interfaz y la validación final de todos los
recorridos sobre una instalación limpia.
