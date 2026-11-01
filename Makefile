.PHONY: test lint

test:
	pytest

lint:
	ruff check sentinel server tools tests
	ruff format --check sentinel server tools tests
