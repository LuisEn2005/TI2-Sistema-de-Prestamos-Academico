"""Servidor aislado usado exclusivamente por las pruebas de navegador."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from prestamos_academicos.compartido.reloj import Reloj
from prestamos_academicos.web import create_app


class RelojE2E(Reloj):
    """Mantiene los recorridos reproducibles aunque CI se ejecute en fin de semana."""

    instante = datetime(2026, 10, 19, 20, 0, tzinfo=timezone.utc)

    def ahora(self):
        return self.instante


ruta = Path(os.environ.get("E2E_DATABASE_PATH", "/tmp/prestamos-academicos-e2e.sqlite"))
ruta.unlink(missing_ok=True)

reloj = RelojE2E()
app = create_app(
    f"sqlite:///{ruta}", datos_demo=True, secret_key="e2e-local", reloj=reloj)


@app.post("/api/pruebas/avanzar-dia")
def avanzar_dia():
    """Disponible únicamente en este servidor aislado de pruebas de navegador."""
    reloj.instante += timedelta(days=1)
    return {"fecha": reloj.hoy().isoformat()}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("E2E_BACKEND_PORT", "45000")),
            use_reloader=False)
