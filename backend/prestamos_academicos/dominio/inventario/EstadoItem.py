"""
<<valueobject>> EstadoItem (enumeracion)
"""
from enum import Enum


class EstadoItem(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    PRESTADO = "PRESTADO"
    RESERVADO = "RESERVADO"
    EN_MANTENIMIENTO = "EN_MANTENIMIENTO"
    DADO_DE_BAJA = "DADO_DE_BAJA"
    EXTRAVIADO = "EXTRAVIADO"


# Matriz de transiciones permitidas (RF05). DADO_DE_BAJA es terminal.
TRANSICIONES = {
    EstadoItem.DISPONIBLE: {
        EstadoItem.PRESTADO, EstadoItem.RESERVADO,
        EstadoItem.EN_MANTENIMIENTO, EstadoItem.DADO_DE_BAJA, EstadoItem.EXTRAVIADO,
    },
    EstadoItem.RESERVADO: {
        EstadoItem.PRESTADO, EstadoItem.DISPONIBLE,
        EstadoItem.EN_MANTENIMIENTO, EstadoItem.DADO_DE_BAJA, EstadoItem.EXTRAVIADO,
    },
    EstadoItem.PRESTADO: {
        EstadoItem.DISPONIBLE, EstadoItem.EN_MANTENIMIENTO,
        EstadoItem.DADO_DE_BAJA, EstadoItem.EXTRAVIADO,
    },
    EstadoItem.EN_MANTENIMIENTO: {
        EstadoItem.DISPONIBLE, EstadoItem.DADO_DE_BAJA, EstadoItem.EXTRAVIADO,
    },
    EstadoItem.EXTRAVIADO: {EstadoItem.DISPONIBLE, EstadoItem.DADO_DE_BAJA},
    EstadoItem.DADO_DE_BAJA: set(),
}

# Estados que solo pueden fijar los flujos de préstamo y reserva, nunca una edición manual.
ESTADOS_DE_FLUJO = {EstadoItem.PRESTADO, EstadoItem.RESERVADO}


def transicion_permitida(desde: EstadoItem, hacia: EstadoItem) -> bool:
    return hacia in TRANSICIONES[desde]
