# Ansel spec

## Summary

Ansel is a CLI tool that propagates file templates across multiple git repositories, defined
declaratively via `ansel.yaml`. It clones repos locally, applies templates on a new branch,
commits, pushes, and opens the browser to the PR page.

## Configuration

### `ansel.yaml` Location Resolution

1. `--config <path>` flag (explicit, highest priority)
2. Walk up from cwd until `ansel.yaml` is found (like git)
3. Error if not found

### Variable Resolution Order

For each variable referenced as `{{ var }}` in a template:

1. Per-template `vars` block (highest priority)
2. Global `vars` block
3. Environment variable (if value in yaml is `${VAR_NAME}` syntax)
4. Empty string (no error, no warning)

`${VAR_NAME}` syntax is only valid inside `vars` blocks in `ansel.yaml`, not inside template
files. Template files use standard Jinja2 `{{ var }}` syntax exclusively.

### URL Scheme Detection

| Prefix | Protocol |
|---|---|
| `git@` or `ssh://` | SSH |
| `https://` | HTTPS |
| Port in URL (e.g. `git@host:4444/...`) | SSH, port extracted |

## CLI Structure

```
ansel sync               # apply all templates to all repos
ansel repos              # list repos from ansel.yaml
ansel templates          # list templates from ansel.yaml
```

### Global Flags

```
--config, -f   path to ansel.yaml (else walk-up from cwd)
--dry-run      alias for diff behavior on sync
--plan         ask for confirmation before applying each template to each repo
--workdir      override workdir
```

## Flow

- red/green stringent TDD
- use `pytest.mark.parametrize` and shared fixtures in `conftest.py` as much as possible
- `justfile` commands:
  - `just test` — run full test suite
  - `just lint` — ruff
  - `just coverage` — pytest with coverage report
