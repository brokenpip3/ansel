export NIX := "nix develop --command"

test:
	{{NIX}} pytest

lint:
	{{NIX}} ruff check --fix .

coverage:
	{{NIX}} pytest --cov=ansel tests/

pre-commit:
    {{NIX}} pre-commit run --show-diff-on-failure

build:
    {{NIX}} poetry install --no-interaction --no-root && poetry build
