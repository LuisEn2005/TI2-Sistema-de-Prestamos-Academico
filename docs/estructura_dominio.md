# Estructura del dominio

Las clases del modelo están agrupadas por contexto en `backend/prestamos_academicos/dominio/`:

| Carpeta | Contenido |
| --- | --- |
| `shared_kernel/` | Objetos de valor de identidad y roles compartidos |
| `identidad/` | Usuario, perfiles, permisos y autorización por rol |
| `inventario/` | Ítem, libros, equipos, mobiliario y materiales |
| `reservas/` | Reserva, estados y eventos |
| `prestamos/` | Préstamo, detalle, estados y eventos de devolución |
| `sanciones/` | Sanción, monto, estados y eventos |
| `configuracion/` | Políticas de servicio, sanción y modalidades |
| `auditoria/` | Historial de movimientos y tipos de evento |

Cada clase se mantiene en un módulo propio, como en el modelo original. Las clases de datos tienen atributos tipados y los métodos pendientes todavía lanzan `NotImplementedError`. Los enums heredan de `str` y `Enum`.

La API Flask, los casos de uso del MVP y los modelos SQLAlchemy están en carpetas separadas del dominio. Las clases actuales del dominio no son tablas de SQLAlchemy; el prototipo usa tres tablas mínimas mientras se desarrolla el modelo completo.
