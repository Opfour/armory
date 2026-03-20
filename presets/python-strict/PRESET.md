---
name: python-strict
type: preset
description: >
  Full-stack Python enforcement preset. Extends the core review-commit lifecycle with
  test-driven development, automated code review agents, secret scanning, security
  standards, test coverage rules, and pre-edit backups. Use this preset when working on
  Python projects that demand strict quality gates: typed codebases, libraries with
  public APIs, or services handling sensitive data. Bundles 12 packages across skills,
  agents, rules, hooks, and commands into a single install.
metadata:
  version: 1.0.0
preset:
  packages:
    skills:
      - name: pr-review
      - name: code-refiner
      - name: pre-landing-review
      - name: test-harness
    agents:
      - name: code-reviewer
      - name: secret-scanner
    rules:
      - name: commit-standards
      - name: test-standards
      - name: security-standards
    hooks:
      - name: git-protection
      - name: pre-edit-backup
    commands:
      - name: tdd
      - name: refactor
  compatibility:
    platforms: [darwin, linux]
---

# Python Strict Preset

A comprehensive enforcement stack for Python projects that demand high code quality,
test coverage, and security hygiene. Installs 12 packages spanning the full development
lifecycle.

## Included Packages

| Type    | Package             | Role                                               |
| ------- | ------------------- | -------------------------------------------------- |
| Skill   | pr-review           | Diff-based code review across five dimensions      |
| Skill   | code-refiner        | Structural simplification preserving behavior      |
| Skill   | pre-landing-review  | Final merge-readiness gate                         |
| Skill   | test-harness        | Test generation and coverage analysis              |
| Agent   | code-reviewer       | Automated code review on PR submission             |
| Agent   | secret-scanner      | Detects leaked credentials and API keys            |
| Rule    | commit-standards    | Enforces conventional commit message formatting    |
| Rule    | test-standards      | Enforces minimum test coverage thresholds          |
| Rule    | security-standards  | Enforces secure coding patterns                    |
| Hook    | git-protection      | Blocks force-push and branch deletion on main      |
| Hook    | pre-edit-backup     | Creates file backups before destructive edits      |
| Command | tdd                 | Test-driven development workflow command            |
| Command | refactor      | Automated refactoring with safety checks           |

## Workflow

1. **Write tests first** — use the `tdd` command to start with failing tests.
2. **Implement** — write code to make tests pass.
3. **Refine** — run `code-refiner` to reduce complexity.
4. **Review** — `pr-review` catches bugs; `code-reviewer` agent provides automated
   feedback; `secret-scanner` checks for leaked credentials.
5. **Validate** — `test-standards` enforces coverage thresholds; `security-standards`
   enforces secure patterns.
6. **Refactor** — use `refactor` command for safe, automated refactoring.
7. **Gate** — `pre-landing-review` performs final merge-readiness check.
8. **Protect** — `git-protection` prevents force-pushes; `pre-edit-backup` preserves
   file state before destructive operations.

## When to Use

- Python libraries with public APIs that need strict type safety and test coverage.
- Backend services handling user data, payments, or authentication.
- Typed codebases enforcing `mypy --strict` or equivalent.
- Teams adopting test-driven development as a standard practice.

## Relationship to Core

This preset is a superset of `core`. Installing `python-strict` provides everything
in `core` plus Python-specific enforcement. There is no need to install both.
