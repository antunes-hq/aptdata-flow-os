.PHONY: install test lint clean docs docs-serve

install:
	poetry install

test:
	poetry run pytest tests/ -v

test-cov:
	poetry run pytest tests/ -v --cov=smart_data --cov-report=term-missing

lint:
	poetry run ruff check smart_data/ tests/

docs:
	poetry run mkdocs build

docs-serve:
	poetry run mkdocs serve

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf site/
