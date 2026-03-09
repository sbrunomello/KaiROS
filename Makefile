PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: venv deps build run-servo run-web test

venv:
	./scripts/setup_venv.sh

deps:
	./scripts/install_python_deps.sh

build:
	./scripts/build_servo_daemon.sh

run-servo:
	./scripts/run_servo_daemon.sh

run-web:
	./scripts/run_bot.sh

test:
	$(PYTHON) -m pytest -q
