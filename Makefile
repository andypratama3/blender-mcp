.PHONY: check doctor install install-all test

PYTHON ?= python3

check:
	$(PYTHON) scripts/validate_repo.py
	@if command -v bash >/dev/null 2>&1; then bash -n scripts/install.sh && echo "PASS shell syntax"; fi

doctor:
	$(PYTHON) scripts/doctor.py

install:
	./scripts/install.sh --agent opencode

install-all:
	./scripts/install.sh --agent all

test: check

help:
	@echo "make check       validate repo (CI equivalent)"
	@echo "make doctor      check Blender, bridge, and skill install"
	@echo "make install     install skill for OpenCode"
	@echo "make install-all install skill for every supported agent"
