.PHONY: up down logs test test-backend test-frontend test-e2e checks migrate worker-ping demo-rehearsal verify-local-model verify-media-fixtures clean-runtime

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api worker web

migrate:
	docker compose run --rm api alembic upgrade head

test: test-backend test-frontend

test-backend:
	docker compose run --rm -e TEST_DATABASE_URL=postgresql+psycopg://creator_governance:local_dev_only_change_me@postgres:5432/creator_governance api pytest -q

test-frontend:
	docker compose run --rm web pnpm test -- --run

test-e2e:
	docker run --rm -v $(CURDIR)/frontend:/work -v creator-commerce-governance_web_node_modules:/work/node_modules -w /work -e PLAYWRIGHT_BASE_URL=http://host.docker.internal:5173 mcr.microsoft.com/playwright:v1.62.1-noble /work/node_modules/.bin/playwright test

checks:
	python3 scripts/check_public_tree.py
	python3 scripts/check_markdown_links.py

worker-ping:
	docker compose exec worker celery -A ccg_agent.worker.celery_app inspect ping

demo-rehearsal:
	python3 scripts/rehearse_demo.py

verify-local-model:
	docker compose exec -T api python /workspace/scripts/verify_local_ollama.py \
		--api-base http://127.0.0.1:8000 \
		--ollama-base http://host.docker.internal:11434

verify-media-fixtures:
	docker compose exec -T api python /workspace/scripts/verify_media_fixtures.py

clean-runtime:
	@echo "Runtime removal is intentionally manual. Review .runtime/ before deleting anything."
