# https://www.stuartellis.name/articles/just-task-runner/#checking-justfiles

set shell := ["bash", "-uc"]
set dotenv-load := true

# List available recipes
help:
    @just --list

# Setup the project: install uv, environment, and pre-commit hooks
[group('setup')]
bootstrap: clean-venv install-uv install-env run-hooks

[group('ci')]
build:
    uv build -o dist --all-packages

[group('ci')]
publish:
    uv publish

[group('ci')]
publish-package: build publish

# Install uv
[group('env')]
install-uv:
    #!/bin/bash
    if ! command -v uv &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
    uv --version

# Install the virtual environment
[group('env')]
install-env:
    uv sync --all-extras

# Upgrade the virtual environment
[group('env')]
upgrade-env:
    uv sync --refresh --all-extras -U

# Clean the project
[group('env')]
clean-project:
    uv run python -Bc "for p in __import__('pathlib').Path('.').rglob('*.py[co]'): p.unlink()"
    uv run python -Bc "for p in __import__('pathlib').Path('.').rglob('__pycache__'): p.rmdir()"
    rm -rf dist/
    # Clean directories that end with _cache or _report
    find . -type d \( -name '*_report' -o -name '*_cache' \) -print0 | xargs -0 rm -rf

# Remove the virtual environment
[group('env')]
clean-venv:
    rm -rf .venv

# Clean the project
[group('env')]
clean: clean-project clean-venv

# Run the example script
[group('env')]
run-example:
    uv run python examples/user.py

# Install the pre-commit hooks
[group('git-hooks')]
install-pre-commit:
    uv run pre-commit install
    uv run pre-commit install --hook-type pre-push

# Run the pre-commit hooks
[group('git-hooks')]
run-pre-commit:
    uv run pre-commit run --all-files

# Run the pre-push hooks
[group('git-hooks')]
run-pre-push:
    uv run pre-commit run --hook-stage pre-push

# Run the pre-commit hooks
[group('git-hooks')]
run-hooks: install-pre-commit run-pre-commit run-pre-push

[group('utils')]
[no-cd]
code2prompt:
    code2prompt ./ \
        --tokens \
        --relative-paths \
        --include "packages/**,src/**,justfile,*.toml,*.md,*.py,*.prompty,*.yml" \
        --include-priority \
        --exclude "**" \
        --exclude-from-tree

# Format all Justfiles
[group('utils')]
format:
    just --unstable --fmt

# Lint
[group('utils')]
lint:
    uvx ruff check .
    uvx ruff format --check .

[group('git')]
stage-all:
    git add -A

[group('git')]
@generate-commit-message:
    ollama run qwen2.5-coder "'Output a very short commit message of the following diffs. Only output message text to pipe into the commit message:\n$(git diff --cached)'"

[group('git')]
commit-message:
    #!/bin/bash
    R='\033[0;31m' # Red
    Y='\033[0;33m' # Yellow
    B='\033[0;34m' # Blue
    END='\033[0m'  # Reset color

    # Generate the commit message
    COMMIT_MSG=$(just generate-commit-message)

    # Trim leading and trailing whitespace
    COMMIT_MSG_TRIMMED=$(echo "$COMMIT_MSG" | sed 's/^[ \t]*//;s/[ \t]*$//')

    # Check if the first character is a backtick
    FIRST_CHAR=$(echo "$COMMIT_MSG_TRIMMED" | cut -c1)
    if [ "$FIRST_CHAR" = '`' ]; then
        echo -e "${R}Error: ${Y}Commit message generated starts with a backtick.${END}" >&2
        echo -e "${Y}Generated Commit Message: ${B}$COMMIT_MSG_TRIMMED${END}" >&2
        exit 1
    fi
    # Check for JSON or code block patterns
    if echo "$COMMIT_MSG_TRIMMED" | grep -qE '^\{|\`\`\`|^```|^\[|\('; then
        echo -e "${R}Error: ${Y}Commit message contains invalid formatting, e.g., JSON or code blocks.${END}" >&2
        echo -e "${B}Generated Commit Message: ${B}$COMMIT_MSG_TRIMMED${END}" >&2
        exit 1
    fi
    # Ensure the commit message is not empty
    if [ -z "$COMMIT_MSG_TRIMMED" ]; then
        echo -e "${R}Error: ${Y}Commit message is empty.${END}" >&2
        exit 1
    fi
    # Output the commit message
    echo "$COMMIT_MSG_TRIMMED"

[group('git')]
commit-all m="": stage-all
    just commit "{{ m }}"

[group('git')]
commit m="":
    #!/bin/bash
    B='\033[0;34m' # Blue
    Y='\033[0;33m' # Yellow
    END='\033[0m'  # Reset color
    if [ -z "{{ m }}" ]; then
        m=$(just commit-message)
    else
        m="{{ m }}"
    fi
    git commit -m "$m"
    echo -e "${Y}Commit message: ${B}$m${END}"

# amend the last commit
[group('git')]
amend:
    git commit --amend --no-edit
