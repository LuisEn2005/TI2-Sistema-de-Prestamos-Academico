from sqlalchemy import func, select, update

from ....dominio.inventario import EstadoItem, IItemRepository
from .. import mapeador
from ..modelos import ItemDB


def _like(texto):
    escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado.lower()}%"


class SqlAlchemyItemRepository(IItemRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, item):
        fila = self.sesion.get(ItemDB, item.id.valor) if item.id else None
        fila = mapeador.item_a_orm(item, fila)
        self.sesion.add(fila)
        self.sesion.flush()
        return mapeador.item_a_dominio(fila)

    def find_by_id(self, item_id):
        fila = self.sesion.get(ItemDB, item_id)
        return fila and mapeador.item_a_dominio(fila)

    def find_by_codigo(self, codigo):
        fila = self.sesion.scalar(
            select(ItemDB).where(func.lower(ItemDB.codigo) == codigo.strip().lower()))
        return fila and mapeador.item_a_dominio(fila)

    def find_disponible(self):
        filas = self.sesion.scalars(
            select(ItemDB).where(ItemDB.estado == EstadoItem.DISPONIBLE.value).order_by(ItemDB.id))
        return [mapeador.item_a_dominio(f) for f in filas]

    def buscar(self, *, texto=None, tipo=None, categoria=None, estado=None,
               pagina=1, limite=20):
        condiciones = []
        if texto:
            for palabra in texto.split():
                condiciones.append(ItemDB.texto_busqueda.like(_like(palabra), escape="\\"))
        if tipo:
            condiciones.append(ItemDB.tipo == tipo.upper())
        if categoria:
            condiciones.append(func.lower(ItemDB.categoria) == categoria.lower())
        if estado:
            condiciones.append(ItemDB.estado == estado.value)

        total = self.sesion.scalar(select(func.count()).select_from(ItemDB).where(*condiciones))
        filas = self.sesion.scalars(
            select(ItemDB).where(*condiciones)
            .order_by(ItemDB.nombre, ItemDB.id)
            .limit(limite).offset((pagina - 1) * limite)
        )
        return [mapeador.item_a_dominio(f) for f in filas], total

    def categorias(self):
        return list(self.sesion.scalars(
            select(ItemDB.categoria).distinct().order_by(ItemDB.categoria)))

    def cambiar_estado_si(self, item_id, desde, hacia):
        resultado = self.sesion.execute(
            update(ItemDB)
            .where(ItemDB.id == item_id, ItemDB.estado == desde.value)
            .values(estado=hacia.value)
        )
        return resultado.rowcount == 1
