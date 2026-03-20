set dotenv-load := true

default:
    @just --list

# Install packages to ~/.claude/
install:
    uv run scripts/install.py

# Install all packages non-interactively
install-all:
    echo -e "all\ny" | uv run scripts/install.py

# Install by profile (core, developer, security, full)
install-profile profile:
    uv run scripts/install.py --profile {{profile}}

# Regenerate manifest.yaml
manifest:
    uv run scripts/generate_manifest.py

# Package a specific item (e.g., just package skills/pr-review)
package path:
    uv run scripts/package.py {{path}}

# Validate all eval cases
validate:
    uv run scripts/validate_evals.py

# Sync shared templates to consumers
sync-templates:
    uv run scripts/sync_templates.py

# Run tests
test:
    uv run pytest tests/ -v

# Full pre-PR check
check:
    just manifest
    just sync-templates
    just validate
    just test
