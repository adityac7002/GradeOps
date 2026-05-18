.PHONY: dev install migrate reset-db frontend build help

NODE := /Users/adityachauhan/.nvm/versions/node/v20.20.2/bin/node
NPM  := /Users/adityachauhan/.nvm/versions/node/v20.20.2/bin/npm

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all Python dependencies
	python3 -m pip install -r requirements.txt

dev: ## Run FastAPI dev server (hot-reload)
	python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

dev-bg: ## Run FastAPI server in background
	python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

frontend: ## Start Vite dev server (requires Node)
	PATH="$(dir $(NODE)):$(PATH)" $(NPM) --prefix frontend run dev

frontend-install: ## Install frontend npm dependencies
	PATH="$(dir $(NODE)):$(PATH)" $(NPM) --prefix frontend install

frontend-add: ## Add a frontend package (usage: make frontend-add PKG=some-package)
	PATH="$(dir $(NODE)):$(PATH)" $(NPM) --prefix frontend install $(PKG)

build: ## Build frontend production bundle
	PATH="$(dir $(NODE)):$(PATH)" $(NPM) --prefix frontend run build

migrate: ## Apply Alembic migrations
	python3 -m alembic upgrade head

reset-db: ## ⚠️  Delete the SQLite database and recreate schema
	rm -f gradeops.db
	python3 -c "from backend.database import Base, engine; Base.metadata.create_all(engine); print('DB reset OK')"

download-qwen: ## Download Qwen2-VL-2B (~4 GB) for vision grading
	python3 -c "\
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration; \
print('Downloading Qwen2-VL-2B...'); \
AutoProcessor.from_pretrained('Qwen/Qwen2-VL-2B-Instruct'); \
Qwen2VLForConditionalGeneration.from_pretrained('Qwen/Qwen2-VL-2B-Instruct'); \
print('Done!')"

smoke-test: ## Run a quick API smoke test
	@python3 -c "\
import subprocess, json, sys; \
r = subprocess.run(['curl','-s','http://localhost:8000/'],capture_output=True); \
print('API:', json.loads(r.stdout).get('message','up') if r.returncode==0 else 'OFFLINE')"

logs: ## Tail the uvicorn server log
	tail -f /tmp/gradeops.log 2>/dev/null || echo "No log file (use make dev)"
