# Sprint 2 — Identidad e inventario administrable

## Objetivo y resultado

El **Sprint 2 está terminado**. Su objetivo fue convertir el prototipo del Sprint 1 en una base funcional y mantenible para los siguientes incrementos. Los usuarios y recursos fijos fueron reemplazados por identidad, permisos e inventario administrables desde Astro, respaldados por Flask, SQLAlchemy y migraciones Alembic.

El resultado permite autenticar usuarios, administrar perfiles y vinculaciones, consultar el catálogo público, gestionar recursos y registrar la entrega y devolución básica de un ítem. Las reservas, renovaciones, sanciones, auditoría, modalidades y límites efectivos de préstamo siguen asignados a los Sprints 3–6.

## Requisitos cubiertos

| Requisito | Estado al cerrar el Sprint 2 | Trabajo posterior |
| --- | --- | --- |
| RF01 · Usuarios, rol y vinculación | **Completo** | — |
| RF02 · Usuario habilitado | Parcial | Integrar sanciones activas en el Sprint 5. |
| RF03 · Política según perfil | **Completo en asociación** | Aplicar cupos y plazos en los Sprints 3 y 5. |
| RF04 · Ítems y atributos por tipo | **Completo** | — |
| RF05 · Estados del ítem | Parcial | Incorporar el flujo de reserva en el Sprint 4. |
| RF06 · Consulta de disponibilidad | **Completo** | — |
| RF10, RF11 y RF13 · Préstamo y devolución | Parcial | Modalidad, varios ítems, plazo, condición y cupos en el Sprint 3. |
| RNF01, RNF02, RNF04 y RNF06 | Cubiertos para el alcance actual | Validación integral en el Sprint 6. |
| RNF03 · Trazabilidad | Pendiente | Auditoría en el Sprint 6. |

## Funcionalidad implementada

### Identidad, acceso y sesiones

- El agregado `Usuario` admite varios perfiles: estudiante, docente, administrativo, gestor de inventario y administrador del sistema.
- Estudiantes, docentes y administrativos son prestatarios. La habilitación exige cuenta activa, matrícula o vinculación vigente y ausencia de sanción activa.
- Cada perfil prestatario recibe una política de servicio compatible. Las migraciones reparan perfiles heredados que no tenían esa relación.
- El administrador gestiona usuarios y perfiles y concentra los permisos administrativos. El gestor de inventario opera recursos, entregas y devoluciones, y solo consulta los datos necesarios de prestatarios habilitados.
- Siempre debe existir al menos un administrador activo. Un administrador no puede desactivar su propia cuenta ni retirar su propio perfil administrativo.
- Las contraseñas se almacenan con hash de Werkzeug. El login usa un mensaje uniforme para credenciales incorrectas y limita cinco intentos fallidos por dirección y correo durante la ventana configurada.
- Los tokens duran ocho horas e incluyen una versión de sesión. Cambiar o restablecer la contraseña, desactivar o reactivar la cuenta invalida los tokens emitidos antes del cambio.
- El frontend elimina el token ante una respuesta `401`, diferencia una sesión vencida de un fallo de conexión y solo acepta redirecciones de login del mismo origen.

### Inventario y catálogo

- El catálogo usa una tabla común y atributos JSON definidos mediante el registro extensible `TiposItem`. Se incluyen libro, equipo, material y mobiliario.
- Los códigos se normalizan en mayúsculas y la base protege su formato, los campos obligatorios y los estados válidos mediante restricciones `CHECK`.
- La búsqueda pública admite nombre, código, categoría y atributos, además de filtros por tipo, categoría y estado.
- Los comodines `%` y `_` se tratan como texto. La consulta limita `q` a 120 caracteres, `pagina` a 1–100 000 y `limite` a 1–100.
- Las transiciones manuales respetan el estado actual. `DADO_DE_BAJA` es terminal y `PRESTADO` se controla mediante el flujo de préstamos.
- Los datos ficticios opcionales contienen únicamente *Introduction to Algorithms (CLRS)*, *Clean Code: A Handbook of Agile Software Craftsmanship* y *Meta Quest*.

### Préstamo básico integrado

- Un gestor o administrador registra la entrega de un ítem disponible a un prestatario habilitado.
- La transición `DISPONIBLE` → `PRESTADO` es atómica y evita dos entregas simultáneas del mismo recurso.
- La devolución libera el recurso. Un usuario prestatario ve sus propios préstamos; gestores y administradores ven el conjunto operativo.
- El formulario permite buscar prestatarios y recursos, y muestra hasta 50 coincidencias en cada búsqueda. Esto evita depender de los primeros 100 registros del catálogo.

## Arquitectura y persistencia

La solución mantiene separados el dominio, los servicios de aplicación y la infraestructura. `DomainMapper` transforma modelos ORM y objetos del dominio; los repositorios SQLAlchemy se coordinan mediante `SqlAlchemyUnitOfWork`.

Las migraciones se ejecutan al iniciar Flask y también pueden aplicarse con `alembic upgrade head`:

| Migración | Propósito |
| --- | --- |
| `0001` | Esquema mínimo compatible con el MVP del Sprint 1. |
| `0002` | Identidad, perfiles, políticas e inventario extendido. |
| `0003` | Políticas de usuarios heredados y vinculación del personal. |
| `0004` | Normalización y restricciones de integridad. |
| `0005` | Versión revocable de sesión. |
| `0006` | Separación entre administrador y gestor de inventario. |

Al actualizar una base del Sprint 1, los usuarios heredados reciben un perfil de estudiante `HEREDADO-<id>`, política de estudiante, correo provisional `@sin-correo.local` y ninguna contraseña. Un administrador debe revisar su identidad antes de habilitarles acceso. Al actualizar una instalación del Sprint 2 anterior, el gestor activo más antiguo recibe también el perfil de administrador para conservar el acceso administrativo.

## Contrato HTTP

Todas las escrituras reciben objetos JSON y rechazan propiedades desconocidas. Los identificadores aceptados están entre 1 y el máximo entero de 64 bits.

| Método y ruta | Acceso | Propósito |
| --- | --- | --- |
| `GET /api/salud` | Público | Estado de la API. |
| `POST /api/auth/login` | Público | Autenticación y emisión del token. |
| `GET /api/auth/yo` | Sesión | Identidad, perfiles y permisos actuales. |
| `POST /api/auth/cambiar-password` | Sesión | Cambio de contraseña e invalidación de sesiones previas. |
| `GET /api/items` | Público | Búsqueda y paginación del catálogo. |
| `GET /api/items/{id}`, `/tipos`, `/categorias` | Público | Detalle y metadatos del inventario. |
| `POST /api/items`, `PATCH /api/items/{id}` | Inventario | Alta y edición de recursos. |
| `POST /api/items/{id}/estado` | Inventario | Cambio manual permitido de estado. |
| `GET/POST /api/usuarios`, `GET/PATCH /api/usuarios/{id}` | Administrador | Gestión completa de usuarios y perfiles. |
| `GET /api/usuarios/prestatarios` | Gestor o administrador | Lista mínima de usuarios habilitados, con búsqueda opcional `q`. |
| `GET /api/politicas` | Sesión | Consulta de políticas base. |
| `GET /api/prestamos` | Sesión | Préstamos visibles según permisos. |
| `POST /api/prestamos` | Gestor o administrador | Entrega de un recurso. |
| `POST /api/prestamos/{id}/devolucion` | Gestor o administrador | Devolución de un recurso. |

La API usa `400` para entrada inválida, `401` para autenticación ausente o vencida, `403` para permiso insuficiente, `404` para entidades inexistentes, `409` para conflictos, `422` para reglas que impiden la operación y `429` para el límite de intentos de acceso.

## Calidad y automatización

La suite descubre **74 pruebas backend**: 73 se ejecutan localmente con SQLite y una prueba de integración se activa cuando existe `TEST_POSTGRES_URL`. Esa integración crea el esquema con Alembic en PostgreSQL, crea un usuario y un recurso, y completa una entrega y devolución.

Playwright añade **4 pruebas de navegador** en Chromium:

1. búsqueda y detalle del catálogo público;
2. rechazo de una redirección externa en el login;
3. creación de usuario y recurso, entrega y devolución;
4. acceso operativo del gestor y rechazo de la administración de usuarios.

GitHub Actions ejecuta trabajos separados para backend con SQLite, integración con PostgreSQL 16, build y auditoría de Astro, y recorridos Playwright. Los datos de navegador se guardan en una SQLite temporal bajo `/tmp` y se recrean en cada ejecución.

## Límites conocidos

- El préstamo todavía contiene un solo ítem y no calcula modalidad, fecha límite ni condición de devolución.
- Las políticas se consultan, pero sus cupos y plazos todavía no se aplican ni se editan.
- Las reservas, renovaciones, sanciones y la auditoría aún no tienen flujos funcionales.
- El limitador de intentos vive en memoria por proceso; un despliegue con varios procesos requerirá un almacenamiento compartido.
- El listado operativo de préstamos no está paginado en este incremento.
- `DATOS_DEMO=1` agrega datos ficticios y nunca debe usarse para la base final. Una instalación limpia exige una base nueva, `DATOS_DEMO=0` y las credenciales del primer administrador.

## Siguiente incremento

El Sprint 3 implementará modalidades, varios ítems por préstamo, fecha límite según política, condición de devolución y aplicación de cupos por perfil.

## Avance del proyecto

Cada requisito funcional aporta 1/18 y recibe una fracción según el recorrido que ya funciona de extremo a extremo.

| RF | Fracción | RF | Fracción |
| --- | --- | --- | --- |
| RF01 | 1,00 | RF10 | 0,25 |
| RF02 | 0,30 | RF11 | 0,25 |
| RF03 | 0,75 | RF13 | 0,15 |
| RF04 | 1,00 | RF05 | 0,40 |
| RF06 | 1,00 | RF07–09, RF12 y RF14–18 | 0 |

La suma es 5,10 de 18, aproximadamente **28 % del alcance funcional**. Esta cifra mide requisitos terminados o parcialmente utilizables; no representa esfuerzo ni calidad técnica.
