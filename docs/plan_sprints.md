# Plan de sprints y cierre funcional

## Alcance y estado

Este plan parte de los [requisitos originales RF01–RF18 y RNF01–RNF06](analisis_requisitos_modelo_dominio.md). **Sprints 1 y 2 están implementados** ([MVP](mvp_01.md) y [Sprint 2](sprint_02.md)). **Sprints 3–6 están planificados**: describen entregas esperadas, no funcionalidades existentes. La numeración expresa orden de desarrollo; duración, fechas, responsables e incidencias de Jira se definirán con el equipo.

Cada sprint debe entregar una funcionalidad visible en Astro, una API y reglas en Flask, persistencia cuando corresponda y comprobaciones de su recorrido principal. La cobertura parcial de un requisito en un sprint no equivale a su cierre; la tabla de trazabilidad indica dónde quedará completo.

## Sprint 1 — MVP de préstamo básico · Terminado

**Objetivo.** Validar el recorrido central de consultar un recurso, prestarlo y devolverlo.

| Módulo | Backend | Frontend | Resultado comprobable |
| --- | --- | --- | --- |
| Identidad de prueba | Dos usuarios precargados. | Selector de usuario. | Se puede elegir quién recibe el recurso. |
| Inventario de prueba | Tres recursos precargados y consulta de disponibilidad. | Catálogo con estado de cada recurso. | Un préstamo cambia el recurso a «Prestado». |
| Préstamos y devoluciones | Registro, devolución y rechazo de préstamo duplicado. | Formulario y lista de préstamos activos. | La devolución libera el recurso para otro préstamo. |

Se usaron Flask, Astro y SQLAlchemy con SQLite local por defecto. Es una implementación **parcial** de RF01, RF04–RF06, RF10–RF11 y RF13. No hay autenticación, políticas, reservas ni sanciones. Los endpoints, datos de demostración, pruebas y límites se detallan en el [documento del Sprint 1](mvp_01.md).

## Sprint 2 — Identidad e inventario administrable · Terminado

**Objetivo.** Sustituir los datos de demostración por usuarios y recursos gestionados desde el sistema.

- **Backend:** autenticación y autorización por rol; registro y actualización de usuarios, perfiles y estado de matrícula o vinculación; asociación de políticas por perfil; inventario con atributos comunes y específicos para libros, equipos y materiales; estados completos y búsqueda por tipo, categoría o texto; migraciones y base PostgreSQL.
- **Frontend:** acceso según rol, formularios de usuarios y recursos, catálogo público con búsqueda y filtros, detalle de ítem y estado visible.
- **Cierre:** RF01, RF03, RF04 y RF06 completos. RF02 avanza con la verificación de vinculación; RF05 incorpora los estados de inventario, pero su integración con reservas se cerrará en Sprint 4.
- **Demostración:** un encargado registra un recurso y un usuario habilitado; un visitante encuentra el recurso mediante el catálogo sin autenticarse.
- **Resultado:** implementado; ver [Sprint 2](sprint_02.md) para el alcance real, los endpoints y lo que quedó pendiente.

## Sprint 3 — Préstamos completos · Planificado

**Objetivo.** Extender el préstamo básico a las reglas del modelo de dominio.

- **Backend:** préstamos con uno o más ítems; modalidades *in situ* y externa; fecha límite calculada según política y perfil; control de cupos y exclusividad del ítem; devolución con fecha y condición física, incluyendo daño o pérdida; transacciones para cambios coordinados.
- **Frontend:** flujo de entrega con selección de modalidad e ítems, consulta de fechas y préstamos activos, formulario de devolución con condición de cada recurso.
- **Cierre:** RF10 y RF11 completos; RF13 cubre cupos y disponibilidad, y queda pendiente el bloqueo por sanción hasta Sprint 5.
- **Demostración:** un encargado entrega varios recursos, ve el plazo calculado y registra su devolución con el estado individual de cada ítem.

## Sprint 4 — Reservas y renovaciones · Planificado

**Objetivo.** Gestionar solicitudes previas a la entrega y respetar su prioridad.

- **Backend:** reserva por usuario habilitado, ítem y fecha o franja; confirmación, cancelación y expiración con liberación del recurso; conversión de reserva confirmada en préstamo; renovación condicionada a ausencia de reservas pendientes y a la elegibilidad del usuario.
- **Frontend:** solicitud y seguimiento de reservas, cancelación, presentación de vencimientos y acción de renovación con el motivo de aceptación o rechazo.
- **Cierre:** RF05, RF08 y RF09 completos. RF07 y RF12 implementan el flujo de reserva y renovación; su validación contra sanciones activas se cerrará en Sprint 5.
- **Demostración:** una reserva bloquea la disponibilidad según su estado; al cancelarse o expirar libera el recurso, y una reserva pendiente impide renovarlo.

## Sprint 5 — Sanciones y políticas configurables · Planificado

**Objetivo.** Aplicar incumplimientos y permitir cambiar reglas sin modificar código.

- **Backend:** sanción automática por atraso según política; sanción manual por daño o pérdida con motivo, plazo o monto; cierre por cumplimiento o resolución; validación de sanciones activas antes de reservar, prestar o renovar; administración persistente de límites, plazos, modalidades y reglas de sanción.
- **Frontend:** consulta del estado de sanciones, registro y cierre por personal autorizado, mensajes de bloqueo y panel administrativo de políticas.
- **Cierre:** RF02, RF07, RF12, RF13, RF14, RF15, RF16 y RF18 completos. Se comprueba también la aplicación de la política por perfil definida en RF03.
- **Demostración:** un atraso genera la sanción correspondiente; mientras esté activa, el usuario no puede iniciar nuevas operaciones; un administrador cambia una regla desde la interfaz.

## Sprint 6 — Auditoría y entrega integral · Planificado

**Objetivo.** Completar la trazabilidad y validar el sistema entero en su configuración final.

- **Backend:** historial de préstamos, reservas, sanciones y cambios de estado por usuario e ítem; registro de fecha, responsable y observaciones; filtros por fecha y estado; revisión de permisos, integridad de datos, migraciones y despliegue con PostgreSQL.
- **Frontend:** historial consultable y revisión de todos los flujos para visitante, estudiante o personal y administrador, con mensajes y estados coherentes.
- **Cierre:** RF17 y RNF01–RNF06 verificados; regresión de RF01–RF18 sobre PostgreSQL. El sistema deja de depender de datos precargados para funcionar.
- **Demostración final:** recorrer catálogo público, acceso por rol, administración de usuarios e inventario, reserva, préstamo, renovación, devolución, sanción, cambio de política e historial desde la interfaz Astro, con datos persistidos por Flask y SQLAlchemy.

## Trazabilidad de requisitos funcionales

| Requisito | Módulo y funcionalidad | Sprint de cierre |
| --- | --- | --- |
| RF01 | Registro de usuarios, roles y vinculación. | 2 |
| RF02 | Habilitación por vinculación y ausencia de sanciones activas. | 5 |
| RF03 | Política de servicio asociada al perfil. | 2; aplicación integral revisada en 5 |
| RF04 | Registro de recursos y atributos por tipo. | 2 |
| RF05 | Estados completos del recurso, incluidos reserva y devolución. | 4 |
| RF06 | Disponibilidad y búsqueda por tipo, categoría o texto. | 2 |
| RF07 | Reserva de ítem disponible para fecha o franja, solo para usuarios habilitados. | 5 |
| RF08 | Cancelación y expiración con liberación de ítem. | 4 |
| RF09 | Conversión de reserva confirmada en préstamo. | 4 |
| RF10 | Préstamo con ítems, modalidad y plazo calculado. | 3 |
| RF11 | Devolución y evaluación de condición del recurso. | 3 |
| RF12 | Renovación sujeta a prioridad de reservas y elegibilidad. | 5 |
| RF13 | Bloqueo por sanción o límite simultáneo. | 5 |
| RF14 | Sanción automática por devolución tardía. | 5 |
| RF15 | Sanción manual por daño o pérdida. | 5 |
| RF16 | Cierre de sanción por plazo o resolución. | 5 |
| RF17 | Historial completo por usuario e ítem. | 6 |
| RF18 | Administración de políticas sin cambio de código. | 5 |

## Verificación no funcional y criterio de entrega final

| Requisito | Verificación prevista |
| --- | --- |
| RNF01 | PostgreSQL con restricciones, relaciones y migraciones reproducibles. |
| RNF02 | API Flask consumida por Astro en todos los módulos. |
| RNF03 | Bitácora de cambios relevantes con fecha, responsable y referencia. |
| RNF04 | Catálogo público; reserva y préstamo protegidos por autenticación y permisos. |
| RNF05 | Consultas de catálogo con respuesta aceptable para la carga habitual de la escuela. |
| RNF06 | Incorporación de un nuevo tipo de recurso sin rediseñar todo el inventario. |

El **Sprint 6 y el proyecto completo** se aceptarán solo si los 18 requisitos funcionales pueden ejecutarse de extremo a extremo, los seis requisitos no funcionales se comprueban, las operaciones críticas tienen pruebas y la documentación de uso y despliegue refleja el comportamiento real. Las tareas concretas de Jira se crearán posteriormente a partir de este plan; no se asignan aquí identificadores ni fechas ficticias.
