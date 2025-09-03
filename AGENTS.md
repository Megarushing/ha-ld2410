# Repo Contributor Guide

- Your objective is to write code as concise and humanly readable as possible while always following the recommended best practices.
- For LD2410 protocol documentation refer to file custom_components/ld2410/api/const/__init__.py

## The following steps are required before commiting changes:
- Setup the environment:
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.dev.txt
  ```
- Before any commit, make sure to run the linter:
  ```bash
  ruff check . --fix
  ruff format .
  ```
- Execute the full test suite before making PRs:
  ```bash
  pytest
  ```
- Run tests and linters for every code change.
- Snapshots should be kept under the `tests/__snapshots__` folder.

## Pull request rules
- The pull request description must include:
  - A bullet point list of all the changes made
  - A full description reasoning as to why those changes are necessary
  - The test coverage percentage

## Testing convention
- Unit test coverage must be kept above 80%, for every new feature make unit tests that cover the new code.
- For every bugfix please add a unit test that covers the bug against regressions, so it doesn't happen again in the future.
