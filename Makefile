PACKAGE_and_VERSION = $(shell poetry version)
PACKAGE_NAME = aionxapi
PACKAGE_VERSION = $(word 2, $(PACKAGE_and_VERSION))

all: precheck

# -----------------------------------------------------------------------------
# Devel targets
# -----------------------------------------------------------------------------

.PHONY: precheck
precheck:
	black $(PACKAGE_NAME)
	pre-commit run -a
	interrogate -c pyproject.toml

.PHONY: doccheck
doccheck:
	interrogate ${PACKAGE_NAME} tests -vv --omit-covered-files


clean:
	rm -rf .pytest_cache
	find . -name '__pycache__' | xargs rm -rf

