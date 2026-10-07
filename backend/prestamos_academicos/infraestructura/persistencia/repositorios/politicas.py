from sqlalchemy import select

from ....dominio.configuracion import IPoliticaRepository
from .. import mapeador
from ..modelos import PoliticaServicioDB


class SqlAlchemyPoliticaRepository(IPoliticaRepository):
    def __init__(self, sesion):
        self.sesion = sesion

    def save(self, politica):
        fila = self.sesion.get(PoliticaServicioDB, politica.id.valor) if politica.id else None
        fila = fila or PoliticaServicioDB()
        fila.rol_aplicable = politica.rolAplicable.value
        fila.max_items_simultaneos = politica.maxItemsSimultaneos
        fila.dias_prestamo_default = politica.diasPrestamoDefault
        fila.dias_gracia_reserva = politica.diasGraciaReserva
        fila.tipos_recurso_permitidos = politica.tiposRecursoPermitidos
        self.sesion.add(fila)
        self.sesion.flush()
        return mapeador.politica_a_dominio(fila)

    def find_by_rol(self, rol):
        fila = self.sesion.scalar(
            select(PoliticaServicioDB).where(PoliticaServicioDB.rol_aplicable == rol.value))
        return fila and mapeador.politica_a_dominio(fila)

    def find_by_id(self, politica_id):
        fila = self.sesion.get(PoliticaServicioDB, politica_id)
        return fila and mapeador.politica_a_dominio(fila)

    def listar(self):
        filas = self.sesion.scalars(select(PoliticaServicioDB).order_by(PoliticaServicioDB.id))
        return [mapeador.politica_a_dominio(f) for f in filas]
