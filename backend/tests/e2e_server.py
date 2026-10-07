"""Servidor aislado usado exclusivamente por las pruebas de navegador."""

import os
from pathlib import Path

from prestamos_academicos.web import create_app


ruta = Path(os.environ.get("E2E_DATABASE_PATH", "/tmp/prestamos-academicos-e2e.sqlite"))
ruta.unlink(missing_ok=True)

app = create_app(f"sqlite:///{ruta}", datos_demo=True, secret_key="e2e-local")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("E2E_BACKEND_PORT", "45000")),
            use_reloader=False)
