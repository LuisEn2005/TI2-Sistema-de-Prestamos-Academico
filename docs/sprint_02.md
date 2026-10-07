# Sprint 2 — Identidad e inventario administrable

## Objetivo y resultado

El **Sprint 2 está terminado**. Reemplaza los usuarios y recursos fijos del MVP por datos gestionados desde el sistema: usuarios con credenciales, perfiles y políticas, y un inventario con atributos por tipo, estados y búsqueda. Se añadieron autenticación, autorización por rol, migraciones de esquema y las capas de la arquitectura objetivo (repositorios, mapeador, unidad de trabajo y servicios de aplicación) para estos contextos.

Se verificó con 61 pruebas automatizadas (dominio, API y migraciones), con la comprobación de tipos y compilación de Astro y con ejecuciones manuales contra **SQLite y PostgreSQL 16** durante la implementación, incluida la actualización de una base creada por el Sprint 1. La revisión posterior del sprint repitió las pruebas automatizadas sobre SQLite y el build; no repitió la comprobación manual de PostgreSQL. No se ejecutaron pruebas automáticas de la interfaz en un navegador.

## Requisitos

| Requisito | Estado tras el Sprint 2 | Qué falta |
| --- | --- | --- |
| RF01 Registrar usuarios, rol y vinculación | **Completo** | — |
| RF02 Verificar usuario habilitado | Parcial | Sanciones activas (Sprint 5); hoy valida cuenta activa, rol prestatario y matrícula vigente. |
| RF03 Política según perfil | **Completo** en asociación | Aplicar sus límites y plazos al préstamo (Sprints 3 y 5). |
| RF04 Registrar ítems con atributos por tipo | **Completo** | — |
| RF05 Estados del ítem | Parcial | Reserva y su liberación (Sprint 4). |
| RF06 Consultar disponibilidad | **Completo** | — |
| RF10, RF11, RF13 | Siguen parciales | Modalidades, varios ítems, plazo, condición y límites (Sprint 3). |
| RNF01, RNF02, RNF04, RNF06 | Cubiertos para estos contextos | Verificación integral en el Sprint 6. |
| RNF03 Trazabilidad | **No implementado** | Auditoría (Sprint 6). |

## Qué se implementó

### Identidad
- **Usuario con perfiles** (patrón Party/Role): los roles se deducen de los perfiles presentes (`ESTUDIANTE`, `DOCENTE`, `ADMINISTRATIVO`, `GESTOR_INVENTARIO`); un usuario puede tener varios.
- **Autorización** (`ServicioAutorizacionRol`): estudiante, docente y administrativo comparten los permisos de prestatario; el gestor tiene todos. Con varios roles se unen los permisos.
- **Habilitación** (`Usuario.estaHabilitado`): cuenta activa, rol prestatario, vinculación vigente (personal, o estudiante con matrícula vigente) y sin sanción activa. Un gestor sin rol prestatario no recibe préstamos.
- **Políticas de servicio base** por perfil (RF03): estudiante 3 ítems y 7 días; docente y administrativo 5 ítems y 15 días. Al crear un perfil se le asocia la política de su rol. El gestor no tiene política. Son valores iniciales; se vuelven editables en el Sprint 5.
- **Reglas de seguridad:** contraseñas con hash de Werkzeug; mensaje idéntico para correo inexistente y clave incorrecta; bloqueo temporal tras 5 intentos fallidos; un gestor no puede desactivarse ni quitarse su rol, y siempre debe quedar al menos un gestor activo.

### Inventario
- **Catálogo común** con atributos propios en una columna JSON, definidos por un **registro de tipos** (`TiposItem`). Un tipo nuevo se agrega con su subclase y una entrada en el registro, sin cambiar tabla ni API (RNF06; hay una prueba que lo demuestra).
- **Datos de demostración acotados** a tres recursos de la Escuela de Computación: *Introduction to Algorithms (CLRS)*, *Clean Code: A Handbook of Agile Software Craftsmanship* y *Meta Quest*. Los demás tipos se pueden registrar desde la administración sin precargarlos.
- **Estados y transiciones** (`EstadoItem`): `DADO_DE_BAJA` es terminal. `PRESTADO` y `RESERVADO` solo los fijan los flujos de préstamo y reserva; mientras un ítem está en uno de ellos no admite cambios manuales de estado.
- **Búsqueda pública** por texto (nombre, código, categoría y atributos), tipo, categoría y estado, con paginación. Los comodines `%` y `_` se tratan como texto.

### Préstamos (integración mínima)
El préstamo y la devolución del MVP siguen siendo de **un ítem por préstamo**, ahora protegidos: solo los registra un gestor, validan que el usuario esté habilitado, cambian el estado del ítem con un cambio atómico (`DISPONIBLE`→`PRESTADO`) y cada usuario ve solo sus préstamos. Plazos, modalidades y condición de devolución llegan en el Sprint 3.

### Infraestructura
- **Alembic**: `0001` (esquema del MVP, idempotente) y `0002` (este sprint). Se ejecutan al iniciar la aplicación y con la CLI. Una base del Sprint 1 se actualiza conservando datos: los usuarios heredados reciben el perfil de estudiante `HEREDADO-<id>`, un correo provisional `@sin-correo.local` y **ningún acceso** hasta que un gestor les asigne correo y contraseña. La migración `0002` no tiene reversión automática.
- **Claves foráneas** activadas también en SQLite.
- **Repositorios SQLAlchemy**, `DomainMapper` y `SqlAlchemyUnitOfWork` para usuarios, ítems, políticas y préstamos.

## API

Todas las rutas usan JSON. Las protegidas esperan `Authorization: Bearer <token>`; el token dura 8 horas y los permisos se leen de la base en cada petición, por lo que desactivar a un usuario o cambiar sus roles tiene efecto inmediato.

| Método y ruta | Acceso | Propósito |
| --- | --- | --- |
| `GET /api/salud` | Público | Comprobar que la API responde. |
| `POST /api/auth/login` | Público | Obtener token y datos del usuario con sus permisos. |
| `GET /api/auth/yo` | Sesión | Usuario actual. |
| `POST /api/auth/cambiar-password` | Sesión | Cambiar la propia contraseña. |
| `GET /api/items` | Público | Buscar con `q`, `tipo`, `categoria`, `estado`, `pagina`, `limite`. |
| `GET /api/items/{id}`, `/tipos`, `/categorias` | Público | Detalle, tipos con sus campos y categorías. |
| `POST /api/items`, `PATCH /api/items/{id}` | `REGISTRAR_ITEM_INVENTARIO` | Registrar y editar recursos. |
| `POST /api/items/{id}/estado` | `ACTUALIZAR_ESTADO_ITEM` | Cambiar el estado manualmente. |
| `GET/POST /api/usuarios`, `GET/PATCH /api/usuarios/{id}` | `GESTIONAR_USUARIOS_Y_ROLES` | Listar (`q`, `rol`, `activo`, `habilitado`), registrar y editar usuarios y perfiles. |
| `GET /api/politicas` | Sesión | Políticas de servicio por perfil. |
| `GET /api/prestamos` | Sesión | Todos para un gestor; los propios para los demás. |
| `POST /api/prestamos` | `REGISTRAR_ENTREGA_PRESTAMO` | Registrar entrega (`usuario_id`, `item_id`). |
| `POST /api/prestamos/{id}/devolucion` | `REGISTRAR_DEVOLUCION_PRESTAMO` | Registrar devolución. |

Códigos usados: 400 datos inválidos, 401 sin sesión o credenciales incorrectas, 403 sin permiso, 404 inexistente, 409 conflicto de estado o duplicado, 422 operación no permitida por una regla (usuario no habilitado, estado que fijan otros flujos), 429 demasiados intentos de login.

## Frontend

Páginas Astro con un único cliente HTTP (`ApiClient`): catálogo público con filtros y detalle, inicio de sesión, préstamos (entrega y devolución para el gestor; lista propia para los demás), mi cuenta (política y cambio de contraseña), administración de inventario (formulario dinámico según el tipo) y de usuarios (perfiles por rol). La navegación se adapta a los permisos del usuario. El token se guarda en `sessionStorage` y todo el texto de la API se inserta con `textContent`.

El comando `npm run build` ejecuta primero `astro check` y luego genera las seis páginas. Si no se pueden obtener los tipos de recurso, la administración muestra el error y desactiva el alta en lugar de abrir un formulario incompleto. La auditoría de dependencias del frontend no reportó vulnerabilidades al cerrar esta revisión.

## Decisiones y límites

- **Identificadores enteros.** La base usa claves autoincrementales; los objetos de valor `*Id` del dominio aceptan `int` además de `UUID`. Si el equipo prefiere UUID, requiere una migración de claves.
- **Token firmado en lugar de sesión de servidor**: simple y sin CSRF, pero no se puede revocar antes de su vencimiento salvo desactivando la cuenta. No hay cierre de sesión en el servidor.
- **El limitador de intentos es por proceso**; con varios procesos de Flask debe sustituirse por uno compartido.
- **Las políticas no se editan todavía** (RF18, Sprint 5) y **sus límites aún no se aplican** al préstamo.
- **Datos de demostración**: solo se cargan con `DATOS_DEMO=1`. Una base nueva inicia sin usuarios ni recursos ficticios; requiere `ADMIN_CORREO` y `ADMIN_PASSWORD` para crear el primer gestor. Cambiar la variable sobre una base existente no borra registros previos.
- Los documentos de análisis usan «recurso» e «ítem» como sinónimos; la API usa `item`.

## Avance del proyecto

Estimación ponderada: cada requisito funcional vale 1/18 y se le asigna la fracción que ya funciona de extremo a extremo.

| RF | Fracción | RF | Fracción |
| --- | --- | --- | --- |
| RF01 | 1,00 | RF10 | 0,25 |
| RF02 | 0,30 | RF11 | 0,25 |
| RF03 | 0,75 | RF13 | 0,15 |
| RF04 | 1,00 | RF05 | 0,40 |
| RF06 | 1,00 | Resto (RF07–09, RF12, RF14–18) | 0 |

Suma 5,10 de 18, es decir **≈ 28 %** de los requisitos funcionales (el MVP anterior equivalía a ≈ 4 %). Los criterios de aceptación de los Sprints 3–6 siguen sin cumplirse. Es una estimación del equipo de desarrollo, no una medida de esfuerzo ni de calidad.

## Siguiente paso

Sprint 3: modalidades, préstamos de varios ítems, fecha límite según política y modalidad, condición de devolución y límites por perfil.
