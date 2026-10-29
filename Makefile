.PHONY: dev api web test

dev:
	@echo "Starting API on :8000 and web on :3000"
	@(cd backend && uvicorn app.main:app --reload --port 8000 &) && (cd frontend && npm run dev)

api:
	cd backend && uvicorn app.main:app --reload --port 8000

web:
	cd frontend && npm run dev

test:
	cd backend && PROVIDER=mock pytest -q
