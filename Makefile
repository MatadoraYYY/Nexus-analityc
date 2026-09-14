.PHONY: install build test lint serve verify
install:
	python -m pip install -e ".[dev]"
build:
	python -m nexus.pipeline --generate --data data/processed --api site/api/v1
test:
	pytest
lint:
	ruff check .
serve:
	python -m http.server 8000 --directory site
verify: lint test build
