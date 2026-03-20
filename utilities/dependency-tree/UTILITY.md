---
name: dependency-tree
type: utility
description: >
  Parses project dependency configuration files (pyproject.toml, package.json, go.mod)
  and prints a formatted dependency tree to stdout. Auto-detects project type from files
  present in the working directory. Supports depth limiting for large dependency graphs.
  Use this utility when you need to visualize project dependencies, inspect version
  constraints, or get a quick overview of what a project depends on without running
  package manager commands.
metadata:
  version: 1.0.0
utility:
  runtime: python
  entry_point: scripts/dependency_tree.py
  executable: true
---

# dependency-tree

Parse and display project dependencies as a formatted tree.

## Usage

```bash
# Auto-detect project type in current directory
python scripts/dependency_tree.py

# Specify a project path
python scripts/dependency_tree.py /path/to/project

# Limit tree depth
python scripts/dependency_tree.py --depth 1
```

## Output Format

```
Project: my-project (pyproject.toml)
Dependencies:
  requests >=2.28.0
  click ^8.0
  pydantic >=1.10,<3.0

Dev Dependencies:
  pytest >=7.0
  mypy >=1.0
```

The tree groups dependencies by category (runtime vs dev) where the file format supports it. Version constraints are displayed as specified in the source file.

## Supported Formats

| File | Ecosystem | Sections parsed |
|------|-----------|----------------|
| `pyproject.toml` | Python | `[project.dependencies]`, `[project.optional-dependencies]` |
| `package.json` | Node.js | `dependencies`, `devDependencies` |
| `go.mod` | Go | `require` blocks |

## Limitations

- Parses config files directly; does not resolve transitive dependencies.
- TOML parsing requires Python 3.11+ (`tomllib`).
- Does not read lock files (uv.lock, package-lock.json, go.sum).
