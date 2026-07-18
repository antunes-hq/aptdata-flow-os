.PHONY: install test test-cov test-unit test-integration test-e2e lint lint-fix typecheck docs docs-serve clean

install:
	uv sync

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=aptdata --cov-report=term-missing --cov-fail-under=73

test-unit:
	uv run pytest tests/ -v -m "not integration and not e2e"

test-integration:
	uv run pytest tests/test_integration.py -v -m integration

test-e2e:
	uv run pytest tests/test_e2e.py -v -m e2e

lint:
	uv run ruff check aptdata/ tests/

lint-fix:
	uv run ruff check --fix aptdata/ tests/

typecheck:
	uv run mypy aptdata/

docs:
	uv run mkdocs build

docs-serve:
	uv run mkdocs serve

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf site/ coverage.xml .coverage
