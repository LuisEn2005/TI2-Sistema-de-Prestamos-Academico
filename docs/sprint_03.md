# Sprint 3 — Préstamos completos

## Objetivo y resultado

El **Sprint 3 está terminado**. El préstamo básico del Sprint 2 (un ítem, sin plazo) pasó a ser el préstamo del modelo de dominio: **uno o más ítems** por entrega, **modalidad** (en sala o externa), **fecha límite** calculada con la política del perfil, **cupo** y **tipos de recurso** por perfil, y **devolución con la condición de cada ítem** (buen estado, dañado o perdido), que deja cada recurso en el estado que corresponde. Todo ocurre en una sola transacción: una entrega o una devolución se aplica completa o no se aplica.

**Demostración:** un gestor entrega varios recursos a un usuario, ve el plazo y el cupo antes de confirmar, y al devolver indica el estado de cada ítem; los dañados quedan en mantenimiento y los perdidos como extraviados.

## Requisitos cubiertos

| Requisito | Estado al cerrar el Sprint 3 | Trabajo posterior |
| --- | --- | --- |
| RF10 · Préstamo con ítems, modalidad y plazo | **Completo** | — |
| RF11 · Devolución y condición del ítem | **Completo** | — |
| RF13 · Bloqueo por sanción o límite simultáneo | Parcial: cupo por perfil y disponibilidad del ítem | Bloqueo por sanción activa en el Sprint 5. |
| RF03 · Política según perfil | **Aplicada**: cupo, plazo y tipos permitidos | Edición de políticas y revisión integral en el Sprint 5. |
| RF05 · Estados del ítem | Parcial: `PRESTADO`, `EN_MANTENIMIENTO` y `EXTRAVIADO` los fija el flujo de préstamo | `RESERVADO` y su liberación en el Sprint 4. |
| RF02 · Usuario habilitado | Parcial (sin cambios) | Sanciones activas en el Sprint 5. |
| RNF03 · Trazabilidad | Pendiente | El dominio ya emite los eventos de devolución; la auditoría los consume en el Sprint 6. |

## Reglas aplicadas

- **Plazo (RN2).** Los días de préstamo son el **menor** entre los de la modalidad y los de la política del perfil con que se presta. La modalidad actúa como tope (en sala dura un día aunque el perfil permita quince) y la política personaliza el plazo. Con la configuración inicial: estudiante + externa = 7 días, docente + externa = 15 días, cualquiera + en sala = 1 día.
- **Fecha límite.** Se cuenta en días calendario desde la **fecha local de la escuela** (`America/Lima` por defecto, configurable con `ZONA_HORARIA`), no desde UTC: un préstamo hecho a las 19:00 en Lima sigue siendo del mismo día. La devolución se considera a tiempo hasta el propio día límite.
- **Perfil con que se presta.** Un usuario puede tener varios perfiles prestatarios (p. ej. estudiante y docente). El préstamo guarda el `rol_solicitante`; si el usuario tiene más de uno, el gestor debe indicar cuál. Se exige vinculación vigente **en ese perfil**, y su política es la que se aplica.
- **Cupo (RF13).** Los ítems sin devolver del usuario, sumados a los de la entrega, no pueden superar `max_items_simultaneos` de la política del perfil elegido. Se cuenta sobre todos los préstamos activos del usuario y se serializan las entregas concurrentes del mismo usuario (bloqueo de fila en PostgreSQL).
- **Tipos permitidos.** La política limita qué tipos de recurso presta cada perfil (p. ej. el estudiante no recibe mobiliario).
- **Exclusividad del ítem (RN3).** El cambio `DISPONIBLE → PRESTADO` es atómico y, además, un índice único parcial en la base (`detalles_prestamo`, solo filas activas) impide que un ítem figure en dos préstamos sin devolver. Los ítems se bloquean en orden de id para evitar bloqueos cruzados.
- **Entrega todo o nada.** Si un solo ítem no está disponible, excede el cupo o no está permitido, no se presta ninguno y el mensaje nombra los ítems afectados.
- **Devolución completa.** Se indica la condición de **todos** los ítems del préstamo, sin omitir ni añadir otros. Resultado por ítem: `BUEN_ESTADO → DISPONIBLE`, `DANADO → EN_MANTENIMIENTO` (requiere revisión antes de volver a prestarse), `PERDIDO → EXTRAVIADO`. Cada ítem admite una observación de hasta 300 caracteres.
- **Atraso.** Un préstamo activo con la fecha límite pasada se informa como `vencido` con sus `dias_atraso`; al devolverlo, el atraso queda calculado contra la fecha local de la devolución. Se **deriva al consultar**: no hay un proceso que cambie el estado a `VENCIDO`.

## Modelo y persistencia

| Cambio | Detalle |
| --- | --- |
| `modalidades` | Nombre único, días de plazo y estado activo. Se crean «In situ (en sala)» (1 día) y «Externa (a domicilio)» (15 días) al iniciar, sin duplicarse. |
| `detalles_prestamo` | Un ítem por fila, con `activo`, `condicion` y `observacion`. Restricciones: ítem único por préstamo, condición válida e índice único parcial de ítems activos. |
| `prestamos` | Se agregan `rol_solicitante`, la **copia de la modalidad** (`modalidad_id`, `modalidad_nombre`, `modalidad_dias_plazo`) y `fecha_devolucion_esperada`; se elimina `item_id`. Cambiar la configuración después no altera préstamos ya registrados. |

La migración **`0007`** convierte cada préstamo existente en un préstamo de un ítem: el ítem pasa a un detalle (activo si no se había devuelto). Los préstamos anteriores **no tenían modalidad, perfil ni fecha límite**: esos campos quedan vacíos (la interfaz muestra «Sin modalidad (préstamo anterior)» y «sin fecha límite», y nunca se marcan como vencidos) y la condición de los ya devueltos queda sin registrar. El `downgrade` solo conserva el primer ítem de cada préstamo.

Con **PostgreSQL 16** se comprobó que la migración conserva los préstamos de una base del Sprint 2, y que ocho entregas simultáneas del mismo ítem producen exactamente una entrega y siete conflictos, y que dos pedidos simultáneos del mismo usuario no superan su cupo.

## Contrato HTTP

Todas las rutas siguen exigiendo sesión; la entrega y la devolución exigen los permisos de gestor, como antes.

| Método y ruta | Acceso | Propósito |
| --- | --- | --- |
| `GET /api/modalidades` | Sesión | Modalidades con su plazo y estado. |
| `GET /api/prestamos/condiciones?usuario_id&modalidad_id[&rol_solicitante]` | Entrega de préstamos | Previsualiza rol, plazo, fecha límite y cupo con **las mismas reglas** que aplicará la entrega. Si el usuario tiene varios perfiles y no se indica uno, devuelve solo `roles_posibles`. |
| `POST /api/prestamos` | Entrega de préstamos | Cuerpo: `usuario_id`, `item_ids` (1 a 50), `modalidad_id` y, si hace falta, `rol_solicitante`. |
| `POST /api/prestamos/{id}/devolucion` | Devolución de préstamos | Cuerpo: `condiciones`, lista de `{item_id, condicion, observacion?}` que cubre todos los ítems. |
| `GET /api/prestamos` | Sesión | Ahora paginado: `estado` (`activo`, `vencido`, `devuelto`), `pagina`, `limite` (hasta 100). Los gestores ven todos; el resto, solo los propios. |
| `GET /api/prestamos/{id}` | Sesión | Detalle. Un usuario sin permisos de gestor solo accede a sus préstamos (los demás responden `404`). |

Un préstamo se serializa con `items` (código, nombre, tipo, condición y observación de cada uno), `modalidad`, `rol_solicitante`, `fecha_prestamo`, `fecha_limite`, `fecha_devolucion`, `estado` (`activo` o `devuelto`), `vencido` y `dias_atraso`.

Códigos de respuesta: `400` entrada inválida (incluye campos desconocidos), `404` usuario, ítem, modalidad o préstamo inexistente, `409` ítem no disponible o préstamo ya devuelto, `422` regla que impide la operación (usuario no habilitado, sin vinculación vigente, modalidad inactiva, tipo no permitido, cupo excedido, condiciones incompletas).

### Cambios incompatibles respecto del Sprint 2

- `POST /api/prestamos` ya no acepta `item_id`: use `item_ids` y `modalidad_id` (obligatorio).
- `POST /api/prestamos/{id}/devolucion` exige el cuerpo `condiciones`.
- `GET /api/prestamos` devuelve `{prestamos, total, pagina, limite}` en lugar de una lista, y cada préstamo trae `items` en lugar de `item_id`, `item` y `codigo`.
- Nueva dependencia `tzdata` y variable opcional `ZONA_HORARIA`.

## Interfaz (Astro)

La página **Préstamos** se rehízo:

- **Entrega:** búsqueda y selección de usuario, modalidad, perfil (solo si el usuario tiene varios) y **varios recursos** que se agregan a una lista. Antes de confirmar muestra el perfil, el plazo, la fecha límite y el cupo; si no queda cupo, bloquea el registro. Las respuestas obsoletas se descartan: al cambiar usuario o modalidad rápidamente, prevalece siempre la última elección.
- **Consulta:** préstamos con modalidad, fecha límite, estado (activo, vencido con sus días de atraso, devuelto) y los ítems con su condición, filtrables y paginados. Un usuario sin permisos de gestor ve «Mis préstamos» de solo lectura.
- **Devolución:** diálogo con la condición (por defecto «Buen estado») y la observación de cada ítem; el aviso final resume atraso, ítems en mantenimiento y extraviados.

## Calidad y automatización

- **103 pruebas backend** (102 con SQLite y la de PostgreSQL de CI, que se omite sin `TEST_POSTGRES_URL`). Nuevas: reglas del dominio (plazo, atraso, devolución, eventos), entrega, cupos, tipos, perfiles, atomicidad, devolución por condición, atraso con reloj controlado y zona horaria, visibilidad, migración desde una base del Sprint 2 y exclusividad en la base de datos. El reloj es inyectable (`create_app(reloj=...)`) para probar plazos sin esperar días reales.
- Las migraciones se comprobaron sin diferencias respecto de los modelos, con subida, bajada y nueva subida.
- `npm run build` (incluye `astro check`) pasa con 0 errores. El código real de la página se ejecutó sobre jsdom contra un Flask con base de datos, recorriendo entrega con dos ítems, devolución con un ítem dañado, historial y la vista de un estudiante; esa prueba detectó y permitió corregir una carrera de respuestas desordenadas.
- **Playwright:** la prueba de entrega y devolución se actualizó y se agregó un recorrido de varios recursos con condiciones (cinco pruebas en total). **No se ejecutaron en el entorno de desarrollo** (no fue posible descargar Chromium): deben correr en CI o localmente con `npm run test:e2e`.

## Límites y decisiones por validar

- Los plazos de las modalidades (1 y 15 días) y la regla «el menor entre modalidad y política» son decisiones de este sprint, sin respaldo explícito en el enunciado. Conviene validarlas con la docente; las modalidades y políticas se podrán editar desde la interfaz en el Sprint 5.
- El plazo mínimo es de **un día** porque las fechas se calculan por día, no por hora: «en sala» vence al día siguiente. Una regla por horas requeriría otro modelo de plazo.
- La devolución es **completa** (todos los ítems a la vez); no hay devolución parcial.
- Un ítem dañado pasa a `EN_MANTENIMIENTO` y uno perdido a `EXTRAVIADO` automáticamente; la **sanción** correspondiente se genera recién en el Sprint 5.
- `EstadoPrestamo.VENCIDO` existe en el dominio, pero el estado vencido se calcula al consultar; no se guarda.
- Los eventos `PrestamoDevuelto` y `PrestamoDevueltoTarde` ya se generan en el agregado, pero **todavía nada los consume**.
- La renovación (`Prestamo.renovar`) y las reservas siguen sin implementarse (Sprint 4).
- Un usuario que ya cumple su cupo no puede recibir más ítems hasta devolver; el cupo se calcula sobre todos sus préstamos activos aunque hayan sido con otro perfil.

## Siguiente incremento

El Sprint 4 implementará reservas (crear, confirmar, cancelar, expirar), su conversión en préstamo y la renovación condicionada a que no haya reservas pendientes.

## Avance del proyecto

Con el mismo método del Sprint 2 (cada requisito aporta 1/18 según el recorrido que ya funciona de extremo a extremo):

| RF | Fracción | RF | Fracción |
| --- | --- | --- | --- |
| RF01 | 1,00 | RF10 | 1,00 |
| RF02 | 0,30 | RF11 | 1,00 |
| RF03 | 0,90 | RF13 | 0,60 |
| RF04 | 1,00 | RF05 | 0,55 |
| RF06 | 1,00 | RF07–09, RF12 y RF14–18 | 0 |

La suma es 7,35 de 18, aproximadamente **41 % del alcance funcional**. Las fracciones de RF03, RF05 y RF13 son una estimación del equipo del proyecto; la cifra mide requisitos utilizables, no esfuerzo ni calidad técnica.
