SHELL := /bin/zsh
.DEFAULT_GOAL := help

UVICORN ?= .venv/bin/uvicorn
BACKEND_CMD := $(UVICORN) backend.main:app --reload --port 8000
FRONTEND_CMD := cd frontend && npm run predev && npm run dev

.PHONY: help init install backend frontend dev stop clean test-fe test-be

help:
	@echo "Available targets:"
	@echo "  init      - Create .venv, ensure uv is installed, install backend deps via uv, and frontend deps"
	@echo "  install   - Install backend (pip) and frontend (npm) dependencies"
	@echo "  backend   - Start FastAPI backend (uvicorn) on http://localhost:8000"
	@echo "  frontend  - Start Vite frontend on http://localhost:5173"
	@echo "  dev       - Start backend and frontend together; Ctrl+C to stop both"
	@echo "  test-fe   - Run frontend unit tests (Vitest)"
	@echo "  test-be   - Run backend unit tests (pytest)"
	@echo "  stop      - Stop backgrounded dev processes (if any)"
	@echo "  clean     - Remove pid files"

# Initialize Python venv, install uv in venv via pip if needed, install backend with uv, and frontend deps
init:
	@echo "Initializing dev environment..."
	@if [ ! -d .venv ]; then \
	  echo "Creating Python virtual environment (.venv)"; \
	  python3 -m venv .venv; \
	else \
	  echo "Virtual environment already exists (.venv)"; \
	fi
	@echo "Ensuring uv is installed in the venv"
	@if [ ! -x .venv/bin/uv ]; then \
	  echo "Installing uv into .venv via pip"; \
	  .venv/bin/python -m pip install --upgrade pip; \
	  .venv/bin/python -m pip install uv; \
	else \
	  echo "uv already present in .venv"; \
	fi
	@echo "uv version:" && .venv/bin/uv --version || true
	@echo "Installing Python dependencies with uv (in venv)"
	@.venv/bin/uv pip install -r backend/requirements.txt
	@echo "Installing frontend dependencies (npm install)"
	@cd frontend && npm install
	@echo "Done. Activate venv with: source .venv/bin/activate"

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

backend:
	$(BACKEND_CMD)

frontend:
	$(FRONTEND_CMD)

 test-fe:
	cd frontend && npm run test

 test-be:
	@export PYTHONPATH=$(PWD); \
	if [ -x .venv/bin/pytest ]; then \
		PYTHONPATH=$(PWD) .venv/bin/pytest -q backend; \
	else \
		PYTHONPATH=$(PWD) pytest -q backend; \
	fi

# Runs backend and frontend concurrently. Press Ctrl+C to stop both.
# Uses pid files (.backend.pid, .frontend.pid) to ensure both are terminated.
dev:
	@echo "Starting backend and frontend..."
	@set -e; \
	trap 'echo; echo "Shutting down..."; \
	  test -f .backend.pid && kill $$(cat .backend.pid) 2>/dev/null || true; \
	  test -f .frontend.pid && kill $$(cat .frontend.pid) 2>/dev/null || true; \
	  rm -f .backend.pid .frontend.pid' INT TERM EXIT; \
	( $(BACKEND_CMD) & echo $$! > .backend.pid ); \
	( $(FRONTEND_CMD) & echo $$! > .frontend.pid ); \
	echo "Backend:  http://localhost:8000"; \
	echo "Frontend: http://localhost:5173"; \
	wait

# Try to stop any processes started by `make dev`.
stop:
	@echo "Stopping dev processes (if running)..."
	@test -f .backend.pid && kill $$(cat .backend.pid) 2>/dev/null || true
	@test -f .frontend.pid && kill $$(cat .frontend.pid) 2>/dev/null || true
	@rm -f .backend.pid .frontend.pid
	@echo "Stopped."

clean:
	@rm -f .backend.pid .frontend.pid
	@echo "Cleaned pid files."
