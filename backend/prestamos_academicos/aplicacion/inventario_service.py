"""Casos de uso del contexto Inventario (RF04, RF05, RF06)."""

from sqlalchemy.exc import IntegrityError

from ..dominio.errores import ErrorDominio
from ..dominio.inventario import EstadoItem
from ..dominio.inventario.EstadoItem import ESTADOS_DE_FLUJO
from ..dominio.inventario.TiposItem import listar_tipos, obtener_tipo
from . import validacion as v
from .errores import Conflicto, ErrorAplicacion, NoEncontrado

LIMITE_MAXIMO = 100


class InventarioApplicationService:
    def __init__(self, fabrica_uow):
        self._uow = fabrica_uow

    # -- consultas públicas ---------------------------------------------
    def listar_tipos(self):
        return listar_tipos()

    def categorias(self):
        with self._uow() as uow:
            return uow.items.categorias()

    def buscar(self, *, texto=None, tipo=None, categoria=None, estado=None,
               pagina=1, limite=20):
        if tipo:
            try:
                obtener_tipo(tipo)  # valida el nombre del tipo
            except ErrorDominio as e:
                raise ErrorAplicacion(str(e), 400)
        estado_item = None
        if estado:
            try:
                estado_item = EstadoItem(estado.upper())
            except ValueError:
                raise ErrorAplicacion(f"Estado desconocido: {estado!r}.", 400)
        pagina = max(1, pagina)
        limite = min(max(1, limite), LIMITE_MAXIMO)
        with self._uow() as uow:
            items, total = uow.items.buscar(
                texto=texto, tipo=tipo, categoria=categoria, estado=estado_item,
                pagina=pagina, limite=limite)
        return items, total, pagina, limite

    def obtener(self, item_id):
        with self._uow() as uow:
            item = uow.items.find_by_id(item_id)
        if item is None:
            raise NoEncontrado("El recurso no existe.")
        return item

    # -- administración -------------------------------------------------
    def _leer_campos(self, tipo, datos, atributos):
        v.objeto(atributos, "«atributos»")
        validos = {c.clave: c for c in tipo.campos}
        desconocidos = set(atributos) - set(validos)
        if desconocidos:
            raise ErrorAplicacion(
                f"Atributos no válidos para {tipo.nombre}: {', '.join(sorted(desconocidos))}.", 400)
        return {
            clave: v.texto(atributos, clave, obligatorio=campo.obligatorio,
                           maximo=120, etiqueta=campo.etiqueta)
            for clave, campo in validos.items()
        }

    def registrar_item(self, datos):
        datos = v.objeto(datos)
        try:
            tipo = obtener_tipo(v.texto(datos, "tipo", etiqueta="tipo"))
        except ErrorDominio as e:
            raise ErrorAplicacion(str(e), 400)
        item = tipo.clase(
            codigo=v.texto(datos, "codigo", maximo=30, etiqueta="código"),
            nombre=v.texto(datos, "nombre", maximo=160, etiqueta="nombre"),
            categoria=v.texto(datos, "categoria", maximo=80, etiqueta="categoría"),
            estado=EstadoItem.DISPONIBLE,
            **self._leer_campos(tipo, datos, datos.get("atributos") or {}),
        )
        with self._uow() as uow:
            if uow.items.find_by_codigo(item.codigo):
                raise Conflicto(f"Ya existe un recurso con el código {item.codigo}.")
            try:
                guardado = uow.items.save(item)
                uow.commit()
            except IntegrityError:
                raise Conflicto(f"Ya existe un recurso con el código {item.codigo}.")
        return guardado

    def actualizar_item(self, item_id, datos):
        datos = v.objeto(datos)
        with self._uow() as uow:
            item = uow.items.find_by_id(item_id)
            if item is None:
                raise NoEncontrado("El recurso no existe.")
            if "tipo" in datos and str(datos["tipo"]).upper() != item.TIPO:
                raise ErrorAplicacion("No se puede cambiar el tipo de un recurso.", 400)
            tipo = obtener_tipo(item.TIPO)
            if "codigo" in datos:
                nuevo = v.texto(datos, "codigo", maximo=30, etiqueta="código")
                otro = uow.items.find_by_codigo(nuevo)
                if otro and otro.id.valor != item_id:
                    raise Conflicto(f"Ya existe un recurso con el código {nuevo}.")
                item.codigo = nuevo
            if "nombre" in datos:
                item.nombre = v.texto(datos, "nombre", maximo=160, etiqueta="nombre")
            if "categoria" in datos:
                item.categoria = v.texto(datos, "categoria", maximo=80, etiqueta="categoría")
            if "atributos" in datos:
                actuales = item.atributosEspecificos()
                actuales.update(v.objeto(datos["atributos"], "«atributos»"))
                for clave, valor in self._leer_campos(tipo, datos, actuales).items():
                    setattr(item, clave, valor)
            try:
                guardado = uow.items.save(item)
                uow.commit()
            except IntegrityError:
                raise Conflicto("El código indicado ya está en uso.")
        return guardado

    def cambiar_estado(self, item_id, nuevo_estado):
        try:
            nuevo = EstadoItem(str(nuevo_estado).upper())
        except ValueError:
            raise ErrorAplicacion(f"Estado desconocido: {nuevo_estado!r}.", 400)
        if nuevo in ESTADOS_DE_FLUJO:
            raise ErrorAplicacion(
                f"El estado {nuevo.value} solo lo establece el flujo de "
                "préstamos o reservas.", 422)
        with self._uow() as uow:
            item = uow.items.find_by_id(item_id)
            if item is None:
                raise NoEncontrado("El recurso no existe.")
            anterior = item.estado
            if anterior in ESTADOS_DE_FLUJO:
                raise Conflicto(
                    f"El recurso está {anterior.value}: registre la devolución o "
                    "cancele la reserva antes de cambiar su estado.")
            try:
                {
                    EstadoItem.DISPONIBLE: item.marcarDisponible,
                    EstadoItem.EN_MANTENIMIENTO: item.enviarAMantenimiento,
                    EstadoItem.DADO_DE_BAJA: item.darDeBaja,
                    EstadoItem.EXTRAVIADO: item.marcarExtraviado,
                }[nuevo]()
            except ErrorDominio as e:
                raise Conflicto(str(e))
            if not uow.items.cambiar_estado_si(item_id, anterior, nuevo):
                raise Conflicto("El estado del recurso cambió mientras se procesaba la solicitud.")
            uow.commit()
        return item
