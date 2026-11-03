# Sprint 5 — Sanciones y políticas configurables

## Objetivo y estado

El Sprint 5 está **terminado**. Añade sanciones automáticas por atraso, sanciones
manuales por daño o pérdida y una pantalla administrativa para modificar reglas
sin cambiar código.

## Funcionalidades entregadas

| Área | Resultado |
| --- | --- |
| Elegibilidad | Una sanción activa bloquea nuevos préstamos y reservas. |
| Atraso | La devolución tardía genera una sanción según el factor del rol. |
| Daño o pérdida | El gestor registra la incidencia y el estado físico queda en mantenimiento o extraviado. |
| Cierre | El administrador puede cerrar anticipadamente una sanción con su resolución. |
| Configuración | El administrador modifica cupos, factor de atraso, plazos externos y tipos permitidos. |

## Política final normalizada

Las reglas se dividen según lo que realmente las determina:

- `politicas_rol`: cupo compartido y días de sanción por día de atraso;
- `politicas_servicio`: plazo por combinación de rol y modalidad;
- `politica_tipos_recurso`: relación normalizada de tipos permitidos.

Los valores iniciales son 3 operaciones activas para estudiantes y 5 para
docentes o administrativos. El plazo *in situ* es fijo en 1 día; el externo es
7 días para estudiantes y 14 para docentes o administrativos. Préstamos activos
y reservas pendientes o confirmadas consumen el mismo cupo.

## Permisos

El gestor puede consultar y registrar sanciones operativas. Solo el administrador
puede cerrar sanciones, editar políticas y configurar cierres institucionales.
Esta separación evita que la operación diaria permita cambiar sus propias reglas.

## Relación con reservas y préstamos

La elegibilidad se comprueba antes de crear cualquier movimiento. No existe una
validación de renovación porque esa funcionalidad fue descartada. Una devolución
dañada o perdida también resuelve las reservas futuras del recurso: cancela las
confirmadas y rechaza las pendientes para no prometer un ítem no disponible.

## Calidad

Las pruebas verifican sanción automática, caducidad, sanción manual, permisos y
límites de configuración. La normalización definitiva se completa en la migración
`0015_politicas_y_trazabilidad`, descrita en [Sprint 6](sprint-06.md).
