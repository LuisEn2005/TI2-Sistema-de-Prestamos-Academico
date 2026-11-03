# Sistema de Préstamos Académicos

Sistema para administrar recursos de la Escuela de Computación: catálogo, reservas, préstamos, devoluciones, sanciones y trazabilidad. Este repositorio reúne un frontend en **Astro** y una API en **Flask**. El sistema usa **SQLAlchemy**, SQLite para desarrollo local y PostgreSQL para integración y despliegue.

## Estado actual

Los **Sprints 1–6 están terminados**. El Sprint 1 entregó el MVP de préstamo y devolución. El [Sprint 2](docs/sprints/sprint-02.md) incorporó identidad e inventario administrables, el [Sprint 3](docs/sprints/sprint-03.md) completó préstamos y devoluciones, el [Sprint 4](docs/sprints/sprint-04.md) añadió reservas y el [Sprint 5](docs/sprints/sprint-05.md) incorporó sanciones y políticas editables. El [Sprint 6](docs/sprints/sprint-06.md) cierra el sistema con calendario, disponibilidad por fecha, selección manual, cupo compartido, cierres institucionales y trazabilidad. La renovación fue descartada por decisión funcional para mantener un flujo simple y evitar extensiones indefinidas.

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
    calendario_laboral/             Disponibilidad y cierres institucionales
    sanciones/                      Dominio, servicio, repositorio y rutas de sanciones
    compartido/                     Autenticación, validación, errores y reloj
    base_datos/                     SQLAlchemy, unidad de trabajo y migraciones
  alembic.ini                       Configuración de la CLI de migraciones
  tests/                            Pruebas del backend (dominio, API, migraciones)
frontend/
  package.json                      Dependencia y scripts de Astro
  astro.config.mjs                  Proxy de /api para desarrollo
  src/pages/                        Acceso, catálogo, préstamos, cuenta y administración
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
| **4 · Reservas — terminado** | Solicitar, retirar, confirmar, rechazar, cancelar, expirar y convertir una reserva en préstamo. Cierre de RF05 y RF07–RF09. | Estados explícitos, expiración al final del día inicial y vínculo con el préstamo resultante. | Solicitud, seguimiento, gestión y entrega. |
| **5 · Sanciones y configuración — terminado** | Sanciones automáticas y manuales, cierre, bloqueo y políticas administrables. Cierre de RF02 y RF13–RF16, RF18. | Reglas de sanción, elegibilidad y configuración persistente. | Gestión de sanciones y panel de políticas. |
| **6 · Calendario, trazabilidad y entrega — terminado** | Rangos, selección manual, cierres, reprogramación e historial operativo. Verificación conjunta de RF01–RF18 y RNF01–RNF06. | Disponibilidad derivada, eventos de reserva y aplazamientos de préstamo (`0014`–`0015`). | Calendario público, inventario por fecha, gestión de solicitudes e historial. |

El alcance final se valida de extremo a extremo en Astro, Flask, SQLite y PostgreSQL, con permisos por rol, trazabilidad de reservas y aplazamientos, pruebas de API y recorridos Playwright. La planificación de tareas en Jira se mantiene fuera del repositorio.

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

La expiración de reservas también se comprueba al iniciar la aplicación. En una instalación que permanezca encendida debe programarse diariamente, a las 00:01 de `America/Lima`, el comando:

```bash
cd backend
.venv/bin/python -m flask --app prestamos_academicos.web expirar-reservas
```

**Frontend** (en otra terminal):

```bash
cd frontend
npm ci
npm run dev
```

Para comprobar tipos y generar el frontend: `npm run build` (ejecuta `astro check` y `astro build`).

Astro sirve la aplicación en `http://localhost:4321` y redirige `/api` a Flask. La ruta `/` muestra el acceso institucional; el catálogo público está disponible en `/catalogo` sin iniciar sesión. Pruebas del backend:

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

La automatización en [`.github/workflows/ci.yml`](.github/workflows/ci.yml) ejecuta backend con SQLite, una integración sobre PostgreSQL 16, build y auditoría del frontend, y ocho recorridos Playwright. La interfaz está optimizada para equipos de escritorio. Las pruebas usan bases aisladas; no escriben datos ficticios en la base de la instalación final.

## Documentación de referencia

- [Requisitos y modelo de dominio](docs/requisitos.md)
- [Arquitectura, flujo y base de datos](docs/arquitectura.md)
- [Modelo normalizado de préstamos y políticas](docs/base-de-datos-normalizada.md)
- [Implementación y alcance del primer MVP](docs/sprints/sprint-01.md)
- [Sprint 2: identidad e inventario](docs/sprints/sprint-02.md)
- [Sprint 3: préstamos completos](docs/sprints/sprint-03.md)
- [Sprint 4: reservas](docs/sprints/sprint-04.md)
- [Sprint 5: sanciones y políticas configurables](docs/sprints/sprint-05.md)
- [Sprint 6: calendario, trazabilidad y cierre integral](docs/sprints/sprint-06.md)
- [Plan y cierre de requisitos por sprint](docs/sprints/plan.md)

## Recorridos disponibles

- **Visitante:** acceder primero al inicio de sesión o abrir el catálogo público, buscar y filtrar recursos, ver su detalle y revisar su calendario de disponibilidad.
- **Estudiante, docente o administrativo:** iniciar sesión, solicitar o retirar reservas, consultar sus préstamos e historial, revisar sus sanciones y cambiar su contraseña.
- **Gestor de inventario:** administrar recursos, reservas, entregas y devoluciones; también puede registrar sanciones por daño o pérdida.
- **Administrador del sistema:** gestionar usuarios, cerrar sanciones, configurar políticas y administrar feriados, huelgas u otros cierres, además de las operaciones del gestor.

Detalle de endpoints, reglas y límites en los documentos de cada sprint; el [Sprint 1](docs/sprints/sprint-01.md) conserva la evidencia del MVP original.
