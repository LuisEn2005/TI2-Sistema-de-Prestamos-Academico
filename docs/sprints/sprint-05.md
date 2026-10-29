# Sprint 5 — Sanciones y políticas configurables

## Objetivo y resultado

El **Sprint 5 está terminado**. El sistema genera una sanción cuando se devuelve
un préstamo fuera de plazo, permite que el personal registre daños o pérdidas y
bloquea nuevas reservas, préstamos y renovaciones mientras exista una sanción
activa. El administrador puede modificar cupos, plazos, el factor de sanción y
la disponibilidad de las modalidades desde Astro, sin editar el código.

La solución mantiene el alcance deliberadamente simple: existe una sola entidad
`Sancion`, una sola regla numérica de atraso por política y dos pantallas nuevas.
No se incorporó un motor genérico de reglas ni una jerarquía de sanciones.

## Requisitos cubiertos

| Requisito | Resultado |
| --- | --- |
| RF02, RF07 y RF13 | La sanción activa forma parte de la habilitación y bloquea reservas y préstamos. |
| RF12 | La renovación vuelve a comprobar sanciones antes de ampliar el plazo. |
| RF14 | Una devolución tardía genera una sanción automática según la política aplicada al préstamo. |
| RF15 | El gestor o administrador registra daño o pérdida con motivo y duración o monto. |
| RF16 | La sanción se cierra por vencimiento o, con permiso administrativo, por una resolución. |
| RF18 | Cupos, plazos, factor de atraso y modalidades se administran desde la interfaz. |

Con este incremento están implementados **17 de los 18 requisitos funcionales**.
RF17 y la verificación integral no funcional corresponden al Sprint 6.

## Reglas aplicadas

- Cada política por perfil y modalidad define `dias_sancion_por_dia_atraso`.
- Al devolver tarde, la duración es `días de atraso × factor de la política`.
- Las fechas son inclusivas: una sanción de un día termina al final del día en
  que se crea y se considera vencida al comenzar el día siguiente.
- Una sanción manual solo puede originarse por daño o pérdida. Debe incluir un
  motivo y al menos una duración de 1 a 365 días o un monto positivo en soles.
- Una sanción sin duración permanece activa hasta que un administrador registre
  su resolución. Una sanción con duración se cierra al usar nuevamente el sistema
  después de su fecha final.
- El estudiante consulta únicamente sus sanciones. El personal autorizado puede
  consultar todas y registrar sanciones; el cierre anticipado queda reservado al
  administrador.
- Los cambios de política afectan operaciones nuevas. Un préstamo existente
  conserva el plazo y la política histórica que recibió al ser creado.

## Persistencia

La migración `0013_sanciones_y_configuracion` agrega el factor de atraso a
`politicas_servicio` y crea `sanciones` con las referencias al usuario, al préstamo
opcional y al responsable de su registro. También guarda origen, motivo, monto
opcional, vigencia, estado y resolución.

La base refuerza los estados y orígenes permitidos, el orden de las fechas, los
montos positivos y la correspondencia entre monto y moneda. Los índices por
usuario/estado y préstamo atienden las consultas habituales. La caché de
habilitación del usuario se actualiza en la misma transacción que crea o cierra
la sanción.

## Contrato HTTP

| Método y ruta | Acceso | Propósito |
| --- | --- | --- |
| `GET /api/sanciones?estado=...` | Sesión | Lista las sanciones propias o todas para el personal autorizado. |
| `POST /api/sanciones` | Gestor o administrador | Registra una sanción manual por daño o pérdida. |
| `POST /api/sanciones/{id}/cierre` | Administrador | Cierra una sanción e indica su resolución. |
| `PATCH /api/politicas/{id}` | Administrador | Cambia cupo, plazo o factor de atraso. |
| `PATCH /api/modalidades/{id}` | Administrador | Activa o desactiva una modalidad. |

La devolución conserva su contrato y añade `sancion_generada_id` cuando el atraso
produjo una sanción automática.

## Interfaz Astro

La página **Sanciones** muestra origen, motivo, monto, vigencia y estado. El
personal autorizado obtiene un formulario breve para registrar daño o pérdida y
el administrador puede cerrar una sanción indicando la resolución. La página
**Configuración del servicio** presenta modalidades y políticas en tablas con
edición directa de los únicos parámetros operativos.

Los mensajes de préstamo, reserva y renovación reutilizan la regla de habilitación
y explican que la operación fue rechazada por una sanción activa.

## Calidad y automatización

- Las pruebas del backend cubren generación automática, factor configurable,
  expiración, bloqueo, sanción manual, permisos, validación y cambios de política.
- La migración y el modelo se validan en SQLite; la CI conserva su recorrido de
  migraciones y operación principal sobre PostgreSQL 16.
- El frontend compila con `astro check` y `astro build`.
- Playwright recorre la edición de una política, el registro de una sanción y su
  cierre, además de los flujos anteriores.

## Límites conocidos

- El sistema usa PEN como única moneda y no procesa pagos.
- El vencimiento es oportunista al consultar u operar; no existe un proceso
  permanente en segundo plano.
- Daño y pérdida se registran manualmente después de evaluar el recurso.
- La bitácora transversal y el historial filtrable se implementarán en el Sprint 6.
