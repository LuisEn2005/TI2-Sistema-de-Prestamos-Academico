# Arranca backend (Flask :5000) y frontend (Astro :4321) juntos.
# Ctrl-C detiene ambos. Astro redirige /api a Flask.
.PHONY: dev backend frontend

dev:
	@[ -f .env ] || { cp .env.example .env; echo ">> Creé .env desde .env.example (edítalo solo para instalación real)."; }
	@trap 'kill 0' INT TERM; \
	$(MAKE) --no-print-directory backend & \
	$(MAKE) --no-print-directory frontend & \
	wait

backend:
	cd backend && .venv/bin/python -m flask --app prestamos_academicos.web run

frontend:
	cd frontend && npm run dev
