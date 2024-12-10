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

[group('ci')]
bump:
    #! /bin/bash

    project_version() {
      grep -E '^version = "[0-9]+\.[0-9]\.[0-9]+"$' ${1:?} | head -n 1 | awk '{print $3}' | tr -d '"'
    }

    BRANCH=${CI_MERGE_REQUEST_SOURCE_BRANCH_NAME:-$CI_COMMIT_BRANCH}
    echo BRANCH \'$BRANCH\'.
    MAJOR_RE='\(MAJOR\)'
    MINOR_RE='\(MINOR\)'
    if [[ "$CI_COMMIT_MESSAGE" =~ $MAJOR_RE ]]; then
      bump=major
    elif [[ "$CI_COMMIT_MESSAGE" =~ $MINOR_RE ]]; then
      bump=minor
    else
      bump=patch
    fi
    git fetch --all
    git checkout -B $BRANCH
    git branch --set-upstream-to=origin/$BRANCH

    ROOT_VERSION=$(project_version ./pyproject.toml)
    uvx bump-my-version bump --current-version $ROOT_VERSION $bump ./pyproject.toml
    NEW_VERSION=$(project_version ./pyproject.toml)

    find . -mindepth 2 -type f -name pyproject.toml | while read pyproject_file; do
        CURRENT_VERSION=$(project_version $pyproject_file)
        uvx bump-my-version bump --current-version $CURRENT_VERSION --new-version $NEW_VERSION $bump $pyproject_file
    done
    uv lock
    MESSAGE="Bump version ($bump): $ROOT_VERSION -> $NEW_VERSION [skip-ci]"
    echo $MESSAGE
    git commit -am "$MESSAGE"
    git tag -am "$MESSAGE" "$NEW_VERSION"
    git push origin $BRANCH -o ci.skip
    git push origin $NEW_VERSION -o ci.skip

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
generate-commit-message:
    @(echo "Generate a concise git commit message (max 72 chars) for these changes:"; \
    echo "\n# Files changed\n\n\`\`\`\n$(git diff --cached --stat --compact-summary)\n\`\`\`\n\n"; \
    echo "\n# Detailed changes\n\n\`\`\`\n$(git diff --cached --unified=1 --minimal)\n\`\`\`\n\n") | \
    ollama run qwen2.5-coder "You are a commit message generator. Output only the commit message text in imperative mood. No formatting, JSON, or code blocks or JSON. Examples: 'Add user authentication', 'Fix memory leak in worker', 'Update API docs'.\n\n"

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
        # Capture both output and exit status
        if ! m=$(just commit-message); then
            echo -e "${R}Error: ${Y}Failed to generate commit message${END}" >&2
            exit 1
        fi
    else
        m="{{ m }}"
    fi
    git commit -m "$m"
    echo -e "${Y}Commit message: ${B}$m${END}"

# amend the last commit
[group('git')]
amend:
    git commit --amend --no-edit
