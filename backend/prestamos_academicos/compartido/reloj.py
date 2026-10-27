"""Reloj de la aplicación. Las fechas límite y los atrasos se miden en la zona de la escuela,
no en UTC: un préstamo hecho a las 19:00 en Lima sigue siendo del mismo día."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ..configuracion import cargar_configuracion


class Reloj:
    def __init__(self, zona=None):
        self.zona = ZoneInfo(zona or cargar_configuracion().zona_horaria)

    def ahora(self):
        return datetime.now(timezone.utc)

    def hoy(self):
        """Fecha local de la escuela."""
        return self.ahora().astimezone(self.zona).date()

    def fecha_local(self, instante):
        if instante.tzinfo is None:
            instante = instante.replace(tzinfo=timezone.utc)
        return instante.astimezone(self.zona).date()
