PYTHON ?= python3
SRC := src tests wsgi.py

.PHONY: install install-dev install-research train serve test lint format docker-build clean

install:
	$(PYTHON) -m pip install -r requirements.txt

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

install-research:
	$(PYTHON) -m pip install -r requirements-research.txt

train:
	PYTHONPATH=src $(PYTHON) -m blockscore_ai.training

serve:
	PYTHONPATH=src $(PYTHON) -m blockscore_ai

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m pyflakes $(SRC)
	$(PYTHON) -m black --check $(SRC)
	$(PYTHON) -m isort --check-only $(SRC)

format:
	$(PYTHON) -m black $(SRC)
	$(PYTHON) -m isort $(SRC)

docker-build:
	docker build -t blockscore-ai .

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache build *.egg-info src/*.egg-info
