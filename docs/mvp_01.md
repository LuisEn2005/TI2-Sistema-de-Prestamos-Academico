# Sprint 1 — Primer MVP: préstamo y devolución de recursos

## Objetivo y resultado

El **Sprint 1 está terminado**. Se implementó un prototipo funcional que permite recorrer la idea central del sistema: **consultar un recurso, entregarlo en préstamo a un usuario y registrar su devolución**. La interfaz y las reglas se mantuvieron deliberadamente simples para validar el flujo completo antes de ampliar el alcance.

El MVP conecta una página Astro con una API Flask. SQLAlchemy persiste usuarios, recursos y préstamos. Por defecto se utiliza una base SQLite local que se crea al iniciar el backend; la conexión puede sustituirse mediante `DATABASE_URL` para usar PostgreSQL.

Los datos iniciales del prototipo son los usuarios **Jesus Perez** y **Luis Ramos**, y los recursos **Introduction to Algorithms (CLRS)**, **Clean Code: A Handbook of Agile Software Craftsmanship** y **Meta Quest**. Si existe una base creada con los nombres de usuario de la primera demostración, el backend actualiza esos dos registros al iniciarse sin duplicarlos.

## Funcionalidades implementadas

| Área | Funcionalidad disponible | Relación con requisitos | Alcance del MVP |
| --- | --- | --- | --- |
| Inventario | Consultar un catálogo con código, nombre, tipo y disponibilidad. | RF04–RF06, **parcial** | Tres recursos de demostración; no hay alta, edición ni búsqueda. |
| Usuarios | Seleccionar uno de los usuarios de demostración para registrar la operación. | RF01, **parcial** | Dos usuarios precargados; no hay registro ni autenticación. |
| Préstamos | Registrar la entrega de un recurso disponible y consultar préstamos activos. | RF10 y RF13, **parcial** | Un recurso por préstamo; se impide una segunda entrega del mismo recurso. |
| Devoluciones | Registrar la devolución y liberar el recurso en el catálogo. | RF11, **parcial** | Se registra la fecha de devolución; no se evalúa daño ni atraso. |

Estas operaciones se pueden completar desde una sola página. La interfaz actualiza el catálogo y la lista de préstamos después de cada acción, y muestra los errores de validación o disponibilidad devueltos por la API.

## Trabajo realizado por componente

### Backend: Flask y SQLAlchemy

- La factoría Flask inicializa la base de datos, crea las tablas del prototipo si faltan y registra las rutas de la API.
- Se definieron tres modelos ORM mínimos: `usuarios`, `recursos` y `prestamos`. El préstamo conserva la referencia al usuario y al recurso, además de las fechas de entrega y devolución.
- Se añadieron casos de uso para listar datos, registrar préstamos y registrar devoluciones. El cambio de disponibilidad y el préstamo se guardan en una misma transacción.
- La carga inicial de dos usuarios y tres recursos es idempotente: al reiniciar la aplicación, los préstamos existentes permanecen y los datos de demostración no se duplican.
- La API valida el cuerpo de la solicitud y devuelve errores HTTP para identificadores inválidos, entidades inexistentes y operaciones repetidas.

| Método y ruta | Propósito |
| --- | --- |
| `GET /api/salud` | Comprobar que Flask responde. |
| `GET /api/usuarios` | Obtener usuarios de demostración. |
| `GET /api/recursos` | Obtener el catálogo y su disponibilidad. |
| `GET /api/prestamos` | Obtener préstamos registrados y su estado. |
| `POST /api/prestamos` | Registrar préstamo con `usuario_id` y `recurso_id`. |
| `POST /api/prestamos/{id}/devolucion` | Registrar la devolución de un préstamo activo. |

### Frontend: Astro

- Se sustituyó la página de espera por una vista única con catálogo, formulario de préstamo y préstamos activos.
- La página consulta la API bajo `/api`, envía las operaciones como JSON y actualiza la información sin recargar el sitio.
- El servidor de desarrollo de Astro redirige `/api` a Flask. La vista utiliza controles HTML comunes y estilos mínimos, también en pantallas pequeñas.

## Recorrido de demostración

1. Iniciar el backend y el frontend con los comandos del [README principal](../README.md).
2. Abrir `http://localhost:4321` y observar los tres recursos disponibles.
3. Elegir un usuario y un recurso; registrar el préstamo. El recurso pasa a «Prestado» y aparece en la lista de préstamos activos.
4. Pulsar «Devolver». El préstamo deja de aparecer como activo y el recurso vuelve a estar disponible.
5. Reiniciar Flask: el estado permanece guardado en la base local.

## Verificación y límites

Las pruebas automatizadas del backend cubren la respuesta de salud, la consulta inicial, el ciclo préstamo–devolución, el rechazo de un segundo préstamo o devolución, los datos inválidos y la persistencia tras reiniciar la aplicación. La compilación de Astro verifica que la página y el código del navegador se generan correctamente. Los comandos de verificación están en el README principal.

Este prototipo **no incluye** autenticación, gestión de usuarios o inventario, reservas, sanciones, políticas de préstamo, renovaciones, auditoría, migraciones ni control de condición del recurso. Tampoco integra todavía los métodos pendientes del modelo de dominio completo. La creación automática de tablas y los datos precargados facilitan la demostración; antes de ampliar el sistema se definirán migraciones y datos administrados formalmente.

## Continuidad hacia el sistema completo

El [plan de Sprints 2–6](plan_sprints.md) asigna los requisitos pendientes y sus criterios de cierre. El Sprint 2 reemplazará los datos precargados por gestión real de usuarios y recursos. El Sprint 6 entregará el sistema completo con RF01–RF18 verificados. Las tareas correspondientes se registrarán en Jira cuando se prepare la planificación del equipo; este documento describe únicamente el alcance implementado y comprobado del Sprint 1.
