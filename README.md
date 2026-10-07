# Sistema de Préstamos Académicos

Sistema para administrar recursos de la Escuela de Computación: catálogo, reservas, préstamos, devoluciones, sanciones y trazabilidad. Este repositorio reúne un frontend en **Astro** y una API en **Flask**. El sistema usa **SQLAlchemy** con SQLite local por defecto; **PostgreSQL** sigue siendo la base de datos objetivo del sistema.

## Estado actual

Los **Sprints 1 y 2 están terminados**. El Sprint 1 entregó el MVP de préstamo y devolución. El [Sprint 2](docs/sprint_02.md) lo convirtió en un sistema con **identidad e inventario administrables**: inicio de sesión, roles y permisos, registro de usuarios con perfiles y políticas de servicio, catálogo público con búsqueda y filtros, y gestión de recursos por tipo y estado. El proyecto está en torno al **25–28 % del alcance total** (método de cálculo en [docs/sprint_02.md](docs/sprint_02.md#avance-del-proyecto)). Los Sprints 3–6 siguen siendo una **planificación**: reservas, sanciones, políticas editables, modalidades, renovaciones y auditoría **no están implementados**.

## Estructura del repositorio

```text
backend/
  pyproject.toml                    Dependencias y metadatos Python
  prestamos_academicos/
    web.py                          Factoría de la aplicación Flask
    api/                            Blueprints Flask por contexto y autenticación
    aplicacion/                     Servicios de aplicación e IUnitOfWork
    dominio/                        Entidades y reglas por contexto
      identidad/ inventario/ reservas/ prestamos/
      sanciones/ configuracion/ auditoria/ shared_kernel/
    infraestructura/
      persistencia/                 Modelos ORM, repositorios, mapeador, unidad de trabajo
      migraciones/                  Migraciones de esquema (Alembic)
  alembic.ini                       Configuración de la CLI de migraciones
  tests/                            Pruebas del backend (dominio, API, migraciones)
frontend/
  package.json                      Dependencia y scripts de Astro
  astro.config.mjs                  Proxy de /api para desarrollo
  src/pages/                        Catálogo, login, préstamos, cuenta y administración
  src/scripts/                      ApiClient, sesión y lógica de cada página
  public/                           Recursos estáticos
docs/                                Análisis y modelo de dominio
README.md                            Guía y plan del proyecto
```

El frontend consume respuestas JSON de `/api`. En desarrollo, Astro redirige esa ruta a Flask. En despliegue se deberá publicar la API bajo el mismo prefijo mediante el servidor web o un proxy. Las entidades del dominio y las clases ORM se mantienen separadas; las migraciones conservan los datos del MVP y actualizan su esquema para los módulos de identidad e inventario.

## Plan de funcionalidades por sprint

La secuencia parte del [Sprint 1 implementado](docs/mvp_01.md) y termina con la entrega integral del Sprint 6. **BE** indica backend Flask, dominio y SQLAlchemy; **FE** indica interfaz Astro. Los códigos RF remiten al [análisis de requisitos](docs/analisis_requisitos_modelo_dominio.md). El cierre de cada requisito y los criterios de aceptación figuran en el [plan detallado](docs/plan_sprints.md).

| Sprint y estado | Módulos y alcance | Backend (BE) | Frontend (FE) |
| --- | --- | --- | --- |
| **1 · MVP — terminado** | Catálogo, usuarios de prueba, préstamo y devolución básicos. RF01, RF04–RF06, RF10–RF11 y RF13 **parciales**. | API JSON, tres tablas SQLAlchemy, datos de demostración y control de disponibilidad. | Una página para consultar, prestar y devolver. |
| **2 · Identidad e inventario — terminado** | Usuarios, roles, vinculación, políticas por perfil e inventario administrable. Cierre de RF01, RF03, RF04 y RF06; avance de RF02 y RF05. | Autenticación, permisos, modelos completos, migraciones y PostgreSQL; catálogo filtrable. | Gestión de usuarios y recursos, filtros y vistas por rol. |
| **3 · Préstamos completos — planificado** | Modalidades, varios ítems, plazos, devolución con condición y límites por perfil. Cierre de RF10–RF11; avance de RF13. | Reglas y transacciones de préstamos; cálculo de fecha límite. | Flujo de entrega, devolución y consulta de préstamos. |
| **4 · Reservas y renovaciones — planificado** | Reservar, cancelar, expirar, convertir reserva en préstamo y renovar. Cierre de RF05, RF08–RF09; avance de RF07 y RF12. | Estados, expiración y reglas de disponibilidad y prioridad. | Reserva, seguimiento y renovación. |
| **5 · Sanciones y configuración — planificado** | Sanciones automáticas y manuales, cierre, bloqueo y políticas administrables. Cierre de RF02, RF07, RF12–RF16 y RF18. | Reglas de sanción, elegibilidad y configuración persistente. | Gestión de sanciones y panel de políticas. |
| **6 · Auditoría y entrega integral — planificado** | Historial y validación de todos los flujos. Cierre de RF17 y verificación conjunta de RF01–RF18 y RNF01–RNF06. | Auditoría, pruebas integradas, migraciones y despliegue con PostgreSQL. | Historial consultable y revisión de todos los recorridos por rol. |

El Sprint 6 solo se considerará terminado cuando **todas las funcionalidades RF01–RF18 operen de extremo a extremo** en Astro, Flask y PostgreSQL, con permisos, trazabilidad y pruebas de los casos principales. La planificación de tareas en Jira se realizará después.

## Puesta en marcha

Se requiere Python 3.10 o superior y Node.js compatible con la versión de Astro indicada en `frontend/package.json`.

**Backend** (en una terminal):

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m flask --app prestamos_academicos.web run --debug
```

La API responde en `http://127.0.0.1:5000/api/salud`. Al iniciar, la aplicación **aplica las migraciones de Alembic** (crea el esquema o actualiza una base del Sprint 1), garantiza las políticas de servicio base y, si `DATOS_DEMO` está activo, carga usuarios y recursos de demostración. En desarrollo se crea `backend/instance/prestamos.sqlite`.

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | Base de datos, por ejemplo `postgresql+psycopg://usuario:clave@localhost:5432/prestamos`. Si falta, se usa SQLite local. |
| `SECRET_KEY` | Clave que firma los tokens de sesión. **Obligatoria en producción**; sin ella se genera una temporal y las sesiones se pierden al reiniciar. |
| `DATOS_DEMO` | `1` (por defecto) carga datos de demostración; use `0` en producción. |
| `ADMIN_CORREO`, `ADMIN_PASSWORD` | Crean el primer gestor si el sistema no tiene ninguno. Con `DATOS_DEMO=0` son la forma de obtener acceso inicial. |

**Cuentas de demostración** (contraseña `demo1234`; solo con `DATOS_DEMO=1`): `admin@escuela.edu` (gestor), `luis.ramos@escuela.edu` (docente y gestor) y `jesus.perez@escuela.edu` (estudiante). **Cámbielas o desactive la demostración fuera del desarrollo.**

El catálogo inicial de una base nueva contiene únicamente *Introduction to Algorithms (CLRS)*, *Clean Code: A Handbook of Agile Software Craftsmanship* y *Meta Quest*. Los datos ya existentes en una base previa se conservan al migrar.

Para ejecutar las migraciones manualmente: `DATABASE_URL=... alembic upgrade head` desde `backend/`.

**Frontend** (en otra terminal):

```bash
cd frontend
npm install
npm run dev
```

Para comprobar tipos y generar el frontend: `npm run build` (ejecuta `astro check` y `astro build`).

Astro sirve la aplicación en `http://localhost:4321` y redirige `/api` a Flask. Pruebas del backend:

```bash
cd backend
.venv/bin/python -m unittest discover -s tests -t . -v
```

## Documentación de referencia

- [Análisis de requisitos y modelo de dominio](docs/analisis_requisitos_modelo_dominio.md)
- [Versión explicativa del análisis](docs/analisis_requisitos_modelo_dominio_humanizado.md)
- [Distribución de los contextos del dominio](docs/estructura_dominio.md)
- [Implementación y alcance del primer MVP](docs/mvp_01.md)
- [Sprint 2: identidad e inventario, API y avance](docs/sprint_02.md)
- [Plan y cierre de requisitos por sprint](docs/plan_sprints.md)

## Recorridos disponibles

- **Visitante:** consultar el catálogo con búsqueda, filtros por tipo, categoría y estado, y ver el detalle de cada recurso, sin iniciar sesión.
- **Estudiante, docente o administrativo:** iniciar sesión, ver su política de servicio, sus préstamos activos y cambiar su contraseña.
- **Gestor de inventario:** registrar y editar recursos, cambiar su estado, registrar usuarios con sus perfiles, activar o desactivar cuentas, y registrar entregas y devoluciones.

Detalle de endpoints, reglas y límites en [docs/sprint_02.md](docs/sprint_02.md); el MVP original se describe en [docs/mvp_01.md](docs/mvp_01.md).
