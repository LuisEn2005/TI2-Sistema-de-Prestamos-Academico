"""Dominio de inventario: recursos, estados y registro extensible de tipos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type

from ..compartido import ErrorDominio, ItemId, TransicionInvalida


class EstadoItem(str, Enum):
    DISPONIBLE = "DISPONIBLE"
    PRESTADO = "PRESTADO"
    RESERVADO = "RESERVADO"
    EN_MANTENIMIENTO = "EN_MANTENIMIENTO"
    DADO_DE_BAJA = "DADO_DE_BAJA"
    EXTRAVIADO = "EXTRAVIADO"


TRANSICIONES = {
    EstadoItem.DISPONIBLE: {
        EstadoItem.PRESTADO, EstadoItem.RESERVADO, EstadoItem.EN_MANTENIMIENTO,
        EstadoItem.DADO_DE_BAJA, EstadoItem.EXTRAVIADO,
    },
    EstadoItem.RESERVADO: {
        EstadoItem.PRESTADO, EstadoItem.DISPONIBLE, EstadoItem.EN_MANTENIMIENTO,
        EstadoItem.DADO_DE_BAJA, EstadoItem.EXTRAVIADO,
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

ESTADOS_DE_FLUJO = {EstadoItem.PRESTADO, EstadoItem.RESERVADO}


def transicion_permitida(desde: EstadoItem, hacia: EstadoItem) -> bool:
    return hacia in TRANSICIONES[desde]


@dataclass
class Item:
    id: Optional[ItemId] = None
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    estado: Optional[EstadoItem] = EstadoItem.DISPONIBLE

    TIPO = "ITEM"

    def _cambiar_estado(self, nuevo: EstadoItem) -> None:
        actual = self.estado or EstadoItem.DISPONIBLE
        if actual == nuevo:
            raise TransicionInvalida(f"El ítem ya está en estado {nuevo.value}.")
        if not transicion_permitida(actual, nuevo):
            raise TransicionInvalida(
                f"No se puede pasar de {actual.value} a {nuevo.value}."
            )
        self.estado = nuevo

    def marcarPrestado(self):
        self._cambiar_estado(EstadoItem.PRESTADO)

    def marcarDisponible(self):
        self._cambiar_estado(EstadoItem.DISPONIBLE)

    def marcarReservado(self):
        self._cambiar_estado(EstadoItem.RESERVADO)

    def marcarExtraviado(self):
        self._cambiar_estado(EstadoItem.EXTRAVIADO)

    def enviarAMantenimiento(self):
        self._cambiar_estado(EstadoItem.EN_MANTENIMIENTO)

    def darDeBaja(self):
        self._cambiar_estado(EstadoItem.DADO_DE_BAJA)

    def estaDisponible(self) -> bool:
        return self.estado == EstadoItem.DISPONIBLE

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {}


@dataclass
class Libro(Item):
    isbn: Optional[str] = None
    autor: Optional[str] = None
    editorial: Optional[str] = None

    TIPO = "LIBRO"

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {"isbn": self.isbn, "autor": self.autor, "editorial": self.editorial}


@dataclass
class Equipo(Item):
    numeroSerie: Optional[str] = None
    marcaModelo: Optional[str] = None

    TIPO = "EQUIPO"

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {"numeroSerie": self.numeroSerie, "marcaModelo": self.marcaModelo}


@dataclass
class Mobiliario(Item):
    tipoMobiliario: Optional[str] = None
    ubicacionHabitual: Optional[str] = None

    TIPO = "MOBILIARIO"

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {
            "tipoMobiliario": self.tipoMobiliario,
            "ubicacionHabitual": self.ubicacionHabitual,
        }


@dataclass
class Material(Item):
    tipoMaterial: Optional[str] = None
    unidadMedida: Optional[str] = None

    TIPO = "MATERIAL"

    def atributosEspecificos(self) -> Dict[str, Any]:
        return {"tipoMaterial": self.tipoMaterial, "unidadMedida": self.unidadMedida}


@dataclass(frozen=True)
class Campo:
    clave: str
    etiqueta: str
    obligatorio: bool = False


@dataclass(frozen=True)
class TipoItem:
    nombre: str
    etiqueta: str
    clase: Type[Item]
    campos: Tuple[Campo, ...]


_TIPOS: Dict[str, TipoItem] = {}


def registrar_tipo(tipo: TipoItem) -> None:
    _TIPOS[tipo.nombre] = tipo


def obtener_tipo(nombre: str) -> TipoItem:
    try:
        return _TIPOS[(nombre or "").upper()]
    except KeyError:
        raise ErrorDominio(
            f"Tipo de recurso desconocido: {nombre!r}. "
            f"Tipos válidos: {', '.join(_TIPOS)}."
        )


def listar_tipos() -> List[TipoItem]:
    return list(_TIPOS.values())


registrar_tipo(TipoItem("LIBRO", "Libro", Libro, (
    Campo("isbn", "ISBN", True), Campo("autor", "Autor", True),
    Campo("editorial", "Editorial"),
)))
registrar_tipo(TipoItem("EQUIPO", "Equipo", Equipo, (
    Campo("numeroSerie", "Número de serie", True),
    Campo("marcaModelo", "Marca y modelo", True),
)))
registrar_tipo(TipoItem("MOBILIARIO", "Mobiliario", Mobiliario, (
    Campo("tipoMobiliario", "Tipo de mobiliario", True),
    Campo("ubicacionHabitual", "Ubicación habitual"),
)))
registrar_tipo(TipoItem("MATERIAL", "Material", Material, (
    Campo("tipoMaterial", "Tipo de material", True),
    Campo("unidadMedida", "Unidad de medida"),
)))


class IItemRepository(ABC):
    @abstractmethod
    def asegurar_tipo(self, codigo: str, nombre: str) -> None: ...

    @abstractmethod
    def save(self, item: Item) -> Item: ...

    @abstractmethod
    def find_by_id(self, item_id: int) -> Optional[Item]: ...

    @abstractmethod
    def find_by_ids(self, item_ids) -> dict: ...

    @abstractmethod
    def find_by_codigo(self, codigo: str) -> Optional[Item]: ...

    @abstractmethod
    def find_disponible(self) -> List[Item]: ...

    @abstractmethod
    def buscar(self, *, texto=None, tipo=None, categoria=None, estado=None,
               pagina=1, limite=20) -> Tuple[List[Item], int]: ...

    @abstractmethod
    def categorias(self) -> List[str]: ...

    @abstractmethod
    def cambiar_estado_si(self, item_id: int, desde: EstadoItem, hacia: EstadoItem) -> bool: ...
