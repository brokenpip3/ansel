# Ansel

Ansel is a minimalistic CLI tool designed to manage boilerplate and shared configuration across multiple git repositories.
pening the PR page in your browser.

https://github.com/user-attachments/assets/8e95268e-8aa7-4742-b7f6-b8d08ec183e2

It declaratively propagates updates and removes manual friction by automating the full workflow: cloning repos locally, applying templates,
executing hooks on a new branch, committing, pushing, and opening the PR page in your browser.

## Why?

Have you ever had to update a github action workflow across 20 repositories? Or 200?

Or maybe you needed to add a couple of new files to all your microservices, but each one needs to be filled with different variables?

I do, and it's a nightmare of copy-pasting, manual PRs, and the constant fear of missing one repository.
Or even worse, a bunch of ad hoc scripts, one per each use case.

That's why I built Ansel for my needs, and I will be happy if it can save you from the same pain.

## Core Features

- **Template propagation**: render and sync jinja2 templates (new and existing)
- **Variable substitution**: use variables in templates and patches, values can also be defined dynamically with a command
- **Structural patching**: update yaml and toml files (or generic regex) while preserving comments and indentation (hopefully XD)
- **Hooks**: run custom scripts or built-ins (like pre-commit) per repository inside the repo context

Check all the options and features in the complete example [here](./ansel-complete-example.yaml).

## Installation

- With pip:

```bash
pip install ansel-cli
```

- With Nix:

```bash
nix run|shell github:brokenpip3/ansel
```

## Quick Start

Create an `ansel.yaml` where you want to execute the synchronization, for example:

```yaml
general:
  commit_message: "chore(ansel): update {{ template_name }} in {{ repo_name }}"

repositories:
  - brokenpip3/*             # automatically find all repos in the brokenpip3 github org
  - other-org/other-repo     # specific repo, set the url, group, default branch and more

templates:
  - .github/dependabot.yml   # just render and sync the template inside the templates dir
  - fix-nix-install:         # more complex patch with variables and operations
      type: patch
      include: [".github/workflows/*.y*ml"]
      vars:
        foobar: "hello world"
        # start any var with !cmd to execute a command and use the output as the variable:
        nix_install_new_ver_hash: "!cmd git ls-remote https://github.com/NixOS/nix-installer-action|head -n 1|awk '{print $1}'"
      operations:
        - engine: yaml
          where:
            uses: "DeterminateSystems/nix-installer-action*"
          update:
            uses: "NixOS/nix-installer-action@{{ nix_install_new_ver_hash }}"
        - engine: yaml
          where:
            uses: "DeterminateSystems/magic-nix-cache-action@*"
          delete: true # delete the step if it exists
```

Run the synchronization:

```bash
ansel sync
```

## Usage

- `ansel sync`: automated propagation to all matched repositories
- `ansel sync --dry-run`: Preview changes without making any modifications
- `ansel sync --plan`: interactive mode to review and confirm each change
- `ansel builtins`: list available hooks and template variables
- `ansel repos`: overview of configured repositories
- `ansel templates`: overview of configured templates and patches

## Notes

- This project does not use any github token env because the author believes that any software that requires a permanent gh token is probably a bad software (strong words from an old man - cit).
  The gh repos are scanned via the public api and since there is no other way to also scan the private repos, the tool will use `gh` (if `gh_cli` is set true) with this flow:
  - `gh auth status`
  - `gh login`
  -  <scanning, patching, syncing, cooking, painting>
  - `gh logout` (don't worry, if you are already logged in 'cause you use gh all the time, it will not log you out)

- This project was built with the assistance of an llm. Every line of code was meticulously reviewed, tested, and approved by a human who is now questioning their life choices.
No robots were harmed during development, though several were forced to explain yaml indentation logic until they questioned their own existence.
