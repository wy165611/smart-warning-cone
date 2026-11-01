.PHONY: test lint firmware competition sync

ARDUINO_CLI ?= arduino-cli
FQBN ?= esp32:esp32:esp32c3:CDCOnBoot=cdc
SKETCHES := sentinel follower worker gateway

test:
	pytest

lint:
	ruff check sentinel server tools tests
	ruff format --check sentinel server tools tests

sync:
	python tools/sync_common.py

firmware:
	@for s in $(SKETCHES); do \
		echo "== $$s"; \
		$(ARDUINO_CLI) compile --fqbn $(FQBN) --warnings all firmware/$$s || exit 1; \
	done

competition:
	$(MAKE) -C competition/challenge-cup all
