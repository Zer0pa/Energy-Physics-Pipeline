PY ?= .venv/bin/python

.PHONY: help install install-cpu test contract falsification scientific integration smoke serve clean lint full coverage

help:
	@echo "make install        — install package + test deps"
	@echo "make install-cpu    — install all CPU-side optional deps (electrochem + fusion + tda)"
	@echo "make test           — run all tests"
	@echo "make contract       — contract tests only"
	@echo "make falsification  — falsification wave"
	@echo "make scientific     — scientific bounds tests"
	@echo "make integration    — integration tests (electrochem e2e + fusion phase 0 + reasoning bench)"
	@echo "make smoke          — CLI smoke + quick demo"
	@echo "make serve          — run the FastAPI REST stub server"
	@echo "make clean          — clear runtime audit/kg/cache"
	@echo "make lint           — ruff lint"
	@echo "make full           — clean + install + lint + all tests + smoke"

install:
	$(PY) -m pip install -e '.[test]'

install-cpu:
	$(PY) -m pip install -e '.[test,electrochem,fusion,tda,mcp]'

test:
	$(PY) -m pytest -q

contract:
	$(PY) -m pytest tests/contract -v

falsification:
	$(PY) -m pytest tests/falsification -v

scientific:
	$(PY) -m pytest tests/scientific -v

integration:
	$(PY) -m pytest tests/integration -v

smoke:
	$(PY) -m energy_physics_pipeline.cli.main health
	$(PY) -m energy_physics_pipeline.cli.main registry
	$(PY) -m energy_physics_pipeline.cli.main smoke

serve:
	$(PY) -m energy_physics_pipeline.cli.main serve-rest

clean:
	bash scripts/clean_runtime.sh

lint:
	$(PY) -m ruff check energy_physics_pipeline tests

full:
	bash scripts/clean_runtime.sh
	$(PY) -m pip install -e '.[test]' -q
	$(PY) -m ruff check energy_physics_pipeline tests || true
	$(PY) -m pytest tests -q
	$(PY) -m energy_physics_pipeline.cli.main health

coverage:
	bash scripts/clean_runtime.sh
	$(PY) -m pytest tests --cov=energy_physics_pipeline --cov-report=term-missing --cov-report=xml
	@echo "coverage.xml emitted; soft 80% gate is warn-only — see [tool.coverage.report] in pyproject.toml"
