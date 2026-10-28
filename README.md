# Sistema de Préstamos Académicos

Sistema para administrar recursos de la Escuela de Computación: catálogo, reservas, préstamos, devoluciones, sanciones y trazabilidad. Este repositorio reúne un frontend en **Astro** y una API en **Flask**. El sistema usa **SQLAlchemy**, SQLite para desarrollo local y PostgreSQL para integración y despliegue.

## Estado actual

Los **Sprints 1–4 están terminados**. El Sprint 1 entregó el MVP de préstamo y devolución. El [Sprint 2](docs/sprints/sprint-02.md) incorporó identidad e inventario administrables y el [Sprint 3](docs/sprints/sprint-03.md) completó préstamos, modalidades, cupos y devoluciones. El [Sprint 4](docs/sprints/sprint-04.md) incorpora **reservas y renovaciones**: solicitud por fecha, confirmación, cancelación, expiración, conversión en préstamo y prioridad de una reserva frente a la renovación. Además, el plazo efectivo queda persistido: 7 días para el perfil estudiante y 15 para docente con la configuración inicial. El proyecto está en torno al **63 % del alcance funcional**. Los Sprints 5–6 continúan planificados: sanciones, políticas editables y auditoría todavía no están terminados.

## Estructura del repositorio

```text
backend/
  pyproject.toml                    Dependencias y metadatos Python
  prestamos_academicos/
    web.py                          Factoría de la aplicación Flask
    configuracion.py                Variables de entorno y carga de .env
    identidad/                      Dominio, servicio, repositorio y rutas de usuarios
    inventario/                     Dominio, servicio, repositorio y rutas del catálogo
    prestamos/                      Dominio, servicio, repositorio y rutas de préstamos
    configuracion_servicio/         Políticas y modalidades
    reservas/                       Dominio, servicio, repositorio y rutas de reservas
    sanciones/ auditoria/           Dominio planificado para Sprints 5–6
    compartido/                     Autenticación, validación, errores y reloj
    base_datos/                     SQLAlchemy, unidad de trabajo y migraciones
  alembic.ini                       Configuración de la CLI de migraciones
  tests/                            Pruebas del backend (dominio, API, migraciones)
frontend/
  package.json                      Dependencia y scripts de Astro
  astro.config.mjs                  Proxy de /api para desarrollo
  src/pages/                        Catálogo, login, préstamos, cuenta y administración
  src/compartido/                   Cliente API, sesión, contratos y utilidades
  src/funcionalidades/              Lógica de identidad, catálogo y préstamos
  tests/e2e/                        Recorridos automatizados con Playwright
docs/                                Requisitos, arquitectura y evidencia por sprint
README.md                            Guía y plan del proyecto
```

El frontend consume respuestas JSON de `/api`. En desarrollo, Astro redirige esa ruta a Flask. En despliegue se deberá publicar la API bajo el mismo prefijo mediante el servidor web o un proxy. Las entidades del dominio y las clases ORM se mantienen separadas; las migraciones conservan los datos del MVP y actualizan su esquema para los módulos de identidad e inventario.

## Plan de funcionalidades por sprint

La secuencia parte del [Sprint 1 implementado](docs/sprints/sprint-01.md) y termina con la entrega integral del Sprint 6. **BE** indica backend Flask, dominio y SQLAlchemy; **FE** indica interfaz Astro. Los códigos RF remiten a los [requisitos](docs/requisitos.md). El cierre de cada requisito y los criterios de aceptación figuran en el [plan detallado](docs/sprints/plan.md).

| Sprint y estado | Módulos y alcance | Backend (BE) | Frontend (FE) |
| --- | --- | --- | --- |
| **1 · MVP — terminado** | Catálogo, usuarios de prueba, préstamo y devolución básicos. RF01, RF04–RF06, RF10–RF11 y RF13 **parciales**. | API JSON, tres tablas SQLAlchemy, datos de demostración y control de disponibilidad. | Una página para consultar, prestar y devolver. |
| **2 · Identidad e inventario — terminado** | Usuarios, roles, vinculación, políticas por perfil e inventario administrable. Cierre de RF01, RF03, RF04 y RF06; avance de RF02 y RF05. | Autenticación, permisos, modelos completos, migraciones y PostgreSQL; catálogo filtrable. | Gestión de usuarios y recursos, filtros y vistas por rol. |
| **3 · Préstamos completos — terminado** | Modalidades, varios ítems, plazos, devolución con condición y límites por perfil. Cierre de RF10–RF11; avance de RF13. | Reglas y transacciones de préstamos; cálculo de fecha límite. | Flujo de entrega, devolución y consulta de préstamos. |
| **4 · Reservas y renovaciones — terminado** | Reservar, cancelar, expirar, convertir reserva en préstamo y renovar. Cierre de RF05, RF08–RF09; avance de RF07 y RF12. | Estados, expiración, prioridad, plazo efectivo y migraciones `0008`–`0009`. | Solicitud, seguimiento, gestión y renovación. |
| **5 · Sanciones y configuración — planificado** | Sanciones automáticas y manuales, cierre, bloqueo y políticas administrables. Cierre de RF02, RF07, RF12–RF16 y RF18. | Reglas de sanción, elegibilidad y configuración persistente. | Gestión de sanciones y panel de políticas. |
| **6 · Auditoría y entrega integral — planificado** | Historial y validación de todos los flujos. Cierre de RF17 y verificación conjunta de RF01–RF18 y RNF01–RNF06. | Auditoría, pruebas integradas, migraciones y despliegue con PostgreSQL. | Historial consultable y revisión de todos los recorridos por rol. |

El Sprint 6 solo se considerará terminado cuando **todas las funcionalidades RF01–RF18 operen de extremo a extremo** en Astro, Flask y PostgreSQL, con permisos, trazabilidad y pruebas de los casos principales. La planificación de tareas en Jira se realizará después.

## Puesta en marcha

Se requiere Python 3.10 o superior y Node.js compatible con la versión de Astro indicada en `frontend/package.json`.

**Backend** (en una terminal):

```bash
cp .env.example .env
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m flask --app prestamos_academicos.web run --debug
```

Edite `.env` antes de iniciar. Para una demostración use `DATOS_DEMO=true`; para una instalación limpia use `DATOS_DEMO=false` y cambie las credenciales iniciales. La API responde en `http://127.0.0.1:5000/api/salud`. Al iniciar, la aplicación aplica las migraciones de Alembic y garantiza las políticas de servicio base. Con la base SQLite predeterminada se usa `backend/instance/prestamos.sqlite`.

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | Base de datos, por ejemplo `postgresql+psycopg://usuario:clave@localhost:5432/prestamos`. Si falta, se usa SQLite local. |
| `SECRET_KEY` | Clave que firma los tokens de sesión. **Obligatoria en producción**; sin ella se genera una temporal y las sesiones se pierden al reiniciar. |
| `DATOS_DEMO` | `0` por defecto: sin usuarios ni recursos ficticios. Use `1` únicamente para pruebas. |
| `ZONA_HORARIA` | Zona en la que se calculan las fechas límite y los atrasos. Por defecto `America/Lima`. |
| `ADMIN_CORREO`, `ADMIN_PASSWORD` | En una base limpia son obligatorios juntos para crear el primer administrador. Después pueden omitirse; la cuenta ya existe en la base. |
| `API_PROXY_TARGET` | Dirección de Flask usada por el proxy de Astro. Por defecto `http://127.0.0.1:5000`. |

**Cuentas de demostración** (contraseña `demo1234`; solo con `DATOS_DEMO=1`): `admin@escuela.edu` (administrador), `luis.ramos@escuela.edu` (docente y gestor de inventario) y `jesus.perez@escuela.edu` (estudiante). **Cámbielas o desactive la demostración fuera del desarrollo.**

Al activar `DATOS_DEMO=1` sobre una base migrada desde el MVP, el arranque repara estas cuentas de demostración de forma idempotente: conserva sus identificadores e historial, y garantiza el correo, la contraseña y los perfiles indicados arriba.

Con `DATOS_DEMO=1`, el catálogo incorpora de forma idempotente 26 recursos representativos de la Escuela de Ciencia de la Computación: ocho libros de algoritmos, ingeniería de software, sistemas, redes, bases de datos e inteligencia artificial; nueve equipos de cómputo, sistemas embebidos, redes y audiovisuales; seis materiales de conectividad, electrónica y energía; y tres muebles para laboratorios y aulas. Si la base ya contiene recursos, solo agrega los códigos faltantes y conserva sus datos y estados actuales.

**Instalación limpia para uso real:** configure una **base nueva** distinta de la usada para pruebas y arranque con `DATOS_DEMO=0`, `SECRET_KEY`, `ADMIN_CORREO` y `ADMIN_PASSWORD`. Por ejemplo, desde `backend/`:

```bash
DATABASE_URL='sqlite:////ruta/absoluta/prestamos-reales.sqlite' \
SECRET_KEY='clave-aleatoria-larga' DATOS_DEMO=0 \
ADMIN_CORREO='admin@escuela.edu' ADMIN_PASSWORD='clave-inicial-segura' \
.venv/bin/python -m flask --app prestamos_academicos.web run
```

El primer acceso se hace con ese administrador; desde **Usuarios** e **Inventario** podrá registrar los datos reales. Las políticas base y el administrador inicial son los únicos registros necesarios. Cambiar `DATOS_DEMO` a `0` sobre una base que ya recibió datos de prueba **no los borra**: para la entrega final use una base nueva y conserve la de pruebas por separado.

Para ejecutar las migraciones manualmente: `DATABASE_URL=... alembic upgrade head` desde `backend/`.

**Frontend** (en otra terminal):

```bash
cd frontend
npm ci
npm run dev
```

Para comprobar tipos y generar el frontend: `npm run build` (ejecuta `astro check` y `astro build`).

Astro sirve la aplicación en `http://localhost:4321` y redirige `/api` a Flask. Pruebas del backend:

```bash
cd backend
.venv/bin/python -m unittest discover
```

Pruebas de navegador, después de instalar Chromium una vez:

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

La automatización en [`.github/workflows/ci.yml`](.github/workflows/ci.yml) ejecuta backend con SQLite, una integración sobre PostgreSQL 16, build y auditoría del frontend, y seis recorridos Playwright. Las pruebas usan bases aisladas; no escriben datos ficticios en la base de la instalación final.

## Documentación de referencia

- [Requisitos y modelo de dominio](docs/requisitos.md)
- [Arquitectura, flujo y base de datos](docs/arquitectura.md)
- [Implementación y alcance del primer MVP](docs/sprints/sprint-01.md)
- [Sprint 2: identidad e inventario](docs/sprints/sprint-02.md)
- [Sprint 3: préstamos completos](docs/sprints/sprint-03.md)
- [Sprint 4: reservas y renovaciones](docs/sprints/sprint-04.md)
- [Sprint 3: préstamos completos](docs/sprints/sprint-03.md)
- [Plan y cierre de requisitos por sprint](docs/sprints/plan.md)

## Recorridos disponibles

- **Visitante:** consultar el catálogo con búsqueda, filtros por tipo, categoría y estado, y ver el detalle de cada recurso, sin iniciar sesión.
- **Estudiante, docente o administrativo:** iniciar sesión, ver su política de servicio, consultar sus préstamos con su fecha límite y cambiar su contraseña.
- **Gestor de inventario:** registrar y editar recursos, cambiar su estado, entregar varios recursos a la vez bajo una modalidad (con plazo y cupo a la vista) y registrar devoluciones indicando la condición de cada ítem. Puede consultar únicamente los prestatarios habilitados necesarios para una entrega.
- **Administrador del sistema:** gestionar usuarios, perfiles y accesos, además de realizar las operaciones de inventario y préstamos.

Detalle de endpoints, reglas y límites en los documentos del [Sprint 2](docs/sprints/sprint-02.md) y [Sprint 3](docs/sprints/sprint-03.md); el [Sprint 1](docs/sprints/sprint-01.md) conserva la evidencia del MVP original.
