# Sistema de Préstamos Académicos

Sistema para administrar recursos de la Escuela de Computación: catálogo, reservas, préstamos, devoluciones, sanciones y trazabilidad. Este repositorio reúne un frontend en **Astro** y una API en **Flask**. El MVP usa **SQLAlchemy** con SQLite local por defecto; **PostgreSQL** sigue siendo la base de datos objetivo del sistema.

## Estado actual

El **Sprint 1 está terminado** y entregó el primer MVP: muestra un catálogo de demostración, registra préstamos de un recurso para usuarios de prueba y permite devolverlos. El backend guarda los cambios en la base de datos y evita prestar un recurso ocupado. El modelo de dominio completo sigue organizado por contextos, pero muchos de sus métodos continúan pendientes (`NotImplementedError`). Los Sprints 2–6 son una **planificación**, no funciones ya implementadas.

## Estructura del repositorio

```text
backend/
  pyproject.toml                    Dependencias y metadatos Python
  prestamos_academicos/
    web.py                          Factoría de la aplicación Flask
    api/                            Rutas HTTP y respuestas JSON
    aplicacion/                     Casos de uso del MVP
    dominio/                        Entidades y reglas por contexto
      identidad/ inventario/ reservas/ prestamos/
      sanciones/ configuracion/ auditoria/ shared_kernel/
    infraestructura/
      persistencia/                 Modelos ORM, sesiones y datos de demostración
  tests/                            Pruebas del backend
frontend/
  package.json                      Dependencia y scripts de Astro
  astro.config.mjs                  Proxy de /api para desarrollo
  src/pages/                        Página del MVP
  src/scripts/                      Interacción con la API
  public/                           Recursos estáticos
docs/                                Análisis y modelo de dominio
README.md                            Guía y plan del proyecto
```

El frontend consume respuestas JSON de `/api`. En desarrollo, Astro redirige esa ruta a Flask. En despliegue se deberá publicar la API bajo el mismo prefijo mediante el servidor web o un proxy. Las entidades del dominio y las clases ORM se mantienen separadas: el MVP usa casos de uso mínimos y tablas propias, mientras el modelo de dominio completo sirve de referencia para los sprints posteriores.

## Plan de funcionalidades por sprint

La secuencia parte del [Sprint 1 implementado](docs/mvp_01.md) y termina con la entrega integral del Sprint 6. **BE** indica backend Flask, dominio y SQLAlchemy; **FE** indica interfaz Astro. Los códigos RF remiten al [análisis de requisitos](docs/analisis_requisitos_modelo_dominio.md). El cierre de cada requisito y los criterios de aceptación figuran en el [plan detallado](docs/plan_sprints.md).

| Sprint y estado | Módulos y alcance | Backend (BE) | Frontend (FE) |
| --- | --- | --- | --- |
| **1 · MVP — terminado** | Catálogo, usuarios de prueba, préstamo y devolución básicos. RF01, RF04–RF06, RF10–RF11 y RF13 **parciales**. | API JSON, tres tablas SQLAlchemy, datos de demostración y control de disponibilidad. | Una página para consultar, prestar y devolver. |
| **2 · Identidad e inventario — planificado** | Usuarios, roles, vinculación, políticas por perfil e inventario administrable. Cierre de RF01, RF03, RF04 y RF06; avance de RF02 y RF05. | Autenticación, permisos, modelos completos, migraciones y PostgreSQL; catálogo filtrable. | Gestión de usuarios y recursos, filtros y vistas por rol. |
| **3 · Préstamos completos — planificado** | Modalidades, varios ítems, plazos, devolución con condición y límites por perfil. Cierre de RF10–RF11; avance de RF13. | Reglas y transacciones de préstamos; cálculo de fecha límite. | Flujo de entrega, devolución y consulta de préstamos. |
| **4 · Reservas y renovaciones — planificado** | Reservar, cancelar, expirar, convertir reserva en préstamo y renovar. Cierre de RF05, RF08–RF09; avance de RF07 y RF12. | Estados, expiración y reglas de disponibilidad y prioridad. | Reserva, seguimiento y renovación. |
| **5 · Sanciones y configuración — planificado** | Sanciones automáticas y manuales, cierre, bloqueo y políticas administrables. Cierre de RF02, RF07, RF12–RF16 y RF18. | Reglas de sanción, elegibilidad y configuración persistente. | Gestión de sanciones y panel de políticas. |
| **6 · Auditoría y entrega integral — planificado** | Historial y validación de todos los flujos. Cierre de RF17 y verificación conjunta de RF01–RF18 y RNF01–RNF06. | Auditoría, pruebas integradas, migraciones y despliegue con PostgreSQL. | Historial consultable y revisión de todos los recorridos por rol. |

El Sprint 6 solo se considerará terminado cuando **todas las funcionalidades RF01–RF18 operen de extremo a extremo** en Astro, Flask y PostgreSQL, con permisos, trazabilidad y pruebas de los casos principales. La planificación de tareas en Jira se realizará después.

## Puesta en marcha del MVP

Se requiere Python 3.10 o superior y Node.js compatible con la versión de Astro indicada en `frontend/package.json`.

**Backend** (en una terminal):

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m flask --app prestamos_academicos.web run --debug
```

La API responde en `http://127.0.0.1:5000/api/salud`. En el primer arranque crea `backend/instance/prestamos.sqlite` y carga dos usuarios y tres recursos de demostración. Para usar PostgreSQL, definir `DATABASE_URL` antes de iniciar Flask, por ejemplo `postgresql+psycopg://usuario:clave@localhost:5432/prestamos`. El MVP crea las tablas si faltan; todavía no realiza migraciones de esquema.

**Frontend** (en otra terminal):

```bash
cd frontend
npm install
npm run dev
```

Astro sirve la página inicial en `http://localhost:4321`. Para ejecutar las pruebas actuales del backend:

```bash
cd backend
.venv/bin/python -m unittest discover -s tests -v
```

## Documentación de referencia

- [Análisis de requisitos y modelo de dominio](docs/analisis_requisitos_modelo_dominio.md)
- [Versión explicativa del análisis](docs/analisis_requisitos_modelo_dominio_humanizado.md)
- [Distribución de los contextos del dominio](docs/estructura_dominio.md)
- [Implementación y alcance del primer MVP](docs/mvp_01.md)
- [Plan y cierre de requisitos por sprint](docs/plan_sprints.md)

## Sprint 1: MVP implementado

El recorrido disponible es **consultar catálogo → seleccionar usuario y recurso → registrar préstamo → registrar devolución**. Todo se realiza desde una página Astro sencilla; los datos se guardan con SQLAlchemy. El alcance, los endpoints, las pruebas y las limitaciones están detallados en [la documentación del Sprint 1](docs/mvp_01.md).
