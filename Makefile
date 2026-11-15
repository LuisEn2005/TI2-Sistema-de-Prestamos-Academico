# Arranca backend (Flask :5000) y frontend (Astro :4321) juntos.
# Ctrl-C detiene ambos. Astro redirige /api a Flask.
.PHONY: dev backend frontend

dev:
	@[ -f .env ] || { cp .env.example .env; echo ">> Creé .env desde .env.example (edítalo solo para instalación real)."; }
	@trap 'kill $$BE $$FE 2>/dev/null' INT TERM; \
	( cd backend && exec .venv/bin/python -m flask --app prestamos_academicos.web run ) & BE=$$!; \
	( cd frontend && exec npm run dev ) & FE=$$!; \
	wait

backend:
	cd backend && exec .venv/bin/python -m flask --app prestamos_academicos.web run

frontend:
	cd frontend && exec npm run dev
