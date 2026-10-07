"""Registro de tipos de recurso (RNF06).

Agregar un nuevo tipo de recurso consiste en definir su subclase de Item y
añadir una entrada aquí: no cambia el esquema de base de datos ni la API.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Type

from ..errores import ErrorDominio
from .Equipo import Equipo
from .Item import Item
from .Libro import Libro
from .Material import Material
from .Mobiliario import Mobiliario


@dataclass(frozen=True)
class Campo:
    clave: str          # nombre del atributo en la clase de dominio
    etiqueta: str       # texto para formularios
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
    Campo("isbn", "ISBN", True), Campo("autor", "Autor", True), Campo("editorial", "Editorial"))))
registrar_tipo(TipoItem("EQUIPO", "Equipo", Equipo, (
    Campo("numeroSerie", "Número de serie", True), Campo("marcaModelo", "Marca y modelo", True))))
registrar_tipo(TipoItem("MOBILIARIO", "Mobiliario", Mobiliario, (
    Campo("tipoMobiliario", "Tipo de mobiliario", True), Campo("ubicacionHabitual", "Ubicación habitual"))))
registrar_tipo(TipoItem("MATERIAL", "Material", Material, (
    Campo("tipoMaterial", "Tipo de material", True), Campo("unidadMedida", "Unidad de medida"))))
