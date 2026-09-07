PYTHON ?= python3
export PYTHONPATH := src

.PHONY: bootstrap test ingest replay experiment reports validate

bootstrap:
	$(PYTHON) -m cicada bootstrap

validate:
	$(PYTHON) -m cicada validate

ingest:
	$(PYTHON) -m cicada ingest-core

replay:
	$(PYTHON) -m cicada replay-known

experiment:
	$(PYTHON) -m cicada run-frontier

reports:
	$(PYTHON) -m cicada reports

test:
	$(PYTHON) -m pytest -q
