# Sprint 4 — Reservas y renovaciones

## Objetivo y resultado

El **Sprint 4 está terminado**. El sistema permite que un estudiante o docente
reserve un recurso para una fecha futura, que un gestor confirme o cancele la
solicitud y que una reserva confirmada se convierta en préstamo. También permite
renovar un préstamo cuando el usuario continúa habilitado y ningún tercero espera
el recurso.

Antes de ampliar el flujo se corrigió el cálculo del plazo. La modalidad conserva
su máximo histórico y el préstamo guarda por separado el plazo realmente aplicado:
**7 días para estudiantes y 15 para docentes**, tanto en la respuesta HTTP como en
la base de datos.

## Requisitos cubiertos

| Requisito | Estado al cerrar el Sprint 4 | Trabajo posterior |
| --- | --- | --- |
| RF05 · Estado reservado y liberación del recurso | **Completo** | — |
| RF07 · Solicitud de reserva | Funcional: usuario habilitado, fecha y política | El bloqueo por sanción se integra en el Sprint 5. |
| RF08 · Cancelación y expiración | **Completo** | — |
| RF09 · Conversión en préstamo | **Completo** | — |
| RF12 · Renovación condicionada | Funcional: estado, plazo, habilitación y reservas | El bloqueo por sanción se integra en el Sprint 5. |
| RNF01–02 · Persistencia y API separada | **Completo** en SQLite y PostgreSQL | — |

## Reglas aplicadas

- La fecha de reserva debe estar entre el día actual y los siguientes 365 días.
- El perfil elegido debe estar vigente y su política debe permitir el tipo de
  recurso y una reserva activa adicional.
- Un ítem solo admite una reserva activa. La base de datos refuerza esta regla con
  un índice único parcial.
- Si el ítem está disponible pasa a `RESERVADO`. Un recurso actualmente prestado
  puede reservarse para una fecha futura, pero permanece `PRESTADO` y la reserva
  impide renovarlo.
- El gestor confirma la reserva. Si el recurso continúa prestado, la confirmación
  se rechaza hasta que se registre la devolución.
- Cancelar o expirar una reserva libera el recurso cuando este estaba reservado.
- Una reserva pendiente vence al superar su fecha más los días de gracia de la
  política. La expiración se ejecuta al consultar u operar con reservas, sin un
  proceso permanente en segundo plano.
- La conversión de una reserva confirmada en préstamo es atómica: vuelve a validar
  usuario, política, modalidad y recurso, registra la relación con la reserva y
  cambia el ítem a `PRESTADO`.
- Cada renovación amplía la fecha límite por el plazo efectivo original. Se rechaza
  si el préstamo fue devuelto, está vencido, proviene del formato anterior sin
  fecha, el usuario dejó de estar habilitado o existe una reserva pendiente.

## Persistencia y migraciones

| Migración | Cambio |
| --- | --- |
| `0008_plazo_efectivo` | Agrega `dias_plazo_aplicado`, reconstruye su valor en préstamos existentes y ajusta el máximo inicial de la modalidad in situ a 15 días. |
| `0009_reservas_renovaciones` | Crea `reservas`, sus restricciones e índice de exclusividad; agrega `reserva_id` y `numero_renovaciones` a `prestamos`. |

Las reservas usan los estados `PENDIENTE`, `CONFIRMADA`, `EXPIRADA`, `CANCELADA`
y `CONVERTIDA`. El préstamo conserva una referencia opcional a la reserva que lo
originó, lo que permite seguir el recorrido completo sin duplicar información.

## Contrato HTTP

| Método y ruta | Acceso | Propósito |
| --- | --- | --- |
| `GET /api/reservas` | Sesión | Lista las reservas propias; un gestor puede consultar todas. |
| `POST /api/reservas` | Prestatario | Solicita una reserva indicando recurso, fecha y perfil cuando corresponda. |
| `POST /api/reservas/{id}/confirmacion` | Gestor | Confirma una reserva pendiente cuyo recurso ya puede separarse. |
| `POST /api/reservas/{id}/cancelacion` | Propietario o gestor | Cancela la reserva y libera el recurso. |
| `POST /api/reservas/{id}/prestamo` | Gestor | Convierte una reserva confirmada en préstamo con la modalidad indicada. |
| `POST /api/prestamos/{id}/renovacion` | Propietario o gestor | Renueva un préstamo elegible. |

## Interfaz Astro

La página **Reservas** permite buscar recursos, elegir la fecha y el perfil de la
solicitud, revisar estados y cancelar reservas propias. Los gestores ven todas las
solicitudes y disponen de las acciones de confirmación, cancelación y conversión.
La página **Préstamos** incorpora la renovación y muestra el nuevo plazo o el motivo
concreto por el que no puede aplicarse.

## Calidad y automatización

- **118 pruebas backend** cubren dominio, API, persistencia, migraciones y el
  recorrido de PostgreSQL; la prueba de PostgreSQL se omite localmente si no existe
  `TEST_POSTGRES_URL`.
- El frontend genera siete páginas con `astro check` sin errores.
- **Seis recorridos Playwright** incluyen el nuevo flujo: el estudiante reserva
  *Clean Code* y el administrador confirma y convierte la reserva en préstamo.
- La CI valida por separado SQLite, PostgreSQL, compilación Astro y navegador.

## Límites conocidos

- La reserva usa una fecha, no una franja horaria.
- Existe una sola reserva activa por recurso; no se implementa una cola de espera.
- La expiración es oportunista al usar la API, no un trabajo programado.
- Las sanciones y las políticas editables corresponden al Sprint 5; la bitácora de
  auditoría y el cierre integral corresponden al Sprint 6.

## Avance del proyecto

Al finalizar este incremento, aproximadamente **11,4 de los 18 requisitos
funcionales (63 %)** cuentan con un recorrido utilizable. La cifra representa
alcance funcional, no esfuerzo: RF02, RF07, RF12 y RF13 se completarán con
sanciones; RF18 con la administración de políticas, y RF17 con la auditoría final.
