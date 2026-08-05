.PHONY: install run web test lint format check clean

PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
ifneq ("$(wildcard $(VENV_PYTHON))","")
PYTHON := $(VENV_PYTHON)
endif

install:
	$(PYTHON) -m pip install -e .[dev]

run:
	$(PYTHON) -m pdf_control.cli

web:
	$(PYTHON) -m pdf_control.cli

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m pytest

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov
