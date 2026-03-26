---
name: commit-standards
type: rule
description: 'Enforces conventional commit format, branch naming conventions, and
  commit message structure for consistent version control history. Covers type prefixes
  (feat, fix, chore, docs, refactor, test, perf, ci, build, style), scope requirements,
  subject line constraints, body formatting, BREAKING CHANGE footers, and merge/squash
  policy. Use this rule when writing commit messages, naming branches, preparing pull
  requests, or establishing git workflow standards. Triggers on "commit message",
  "branch naming", "conventional commits", "git workflow", "commit format", "merge
  strategy", "squash commits".

  '
metadata:
  version: 1.0.0
  scope: global
  applies_to:
    languages: ['*']
  category: content
  tags: [commits, conventional, git, branch-naming]
  difficulty: beginner
---
# Commit Standards

Standards for commit messages, branch naming, and merge strategy across all repositories.

## Commit Message Format

Every commit message follows the conventional commit specification:

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### Type Prefixes

| Type       | When to Use                                      |
| ---------- | ------------------------------------------------ |
| `feat`     | New feature visible to end users                 |
| `fix`      | Bug fix for end users                            |
| `docs`     | Documentation-only changes                       |
| `style`    | Formatting, whitespace, semicolons (no logic)    |
| `refactor` | Code change that neither fixes nor adds features |
| `test`     | Adding or correcting tests                       |
| `perf`     | Performance improvement                          |
| `ci`       | CI/CD configuration changes                      |
| `build`    | Build system or dependency changes               |
| `chore`    | Maintenance tasks, tooling, config               |
| `revert`   | Reverts a previous commit                        |

### Subject Line Rules

- Maximum 72 characters
- Imperative mood ("add feature", not "added feature" or "adds feature")
- Lowercase first word after the colon
- No period at the end
- Describe _what_ the commit does, not _how_

```
# correct
feat(auth): add JWT refresh token rotation
fix(api): prevent null pointer on empty query params
refactor(db): extract connection pooling into shared module

# incorrect
feat(auth): Added JWT refresh token rotation.
fix: fixed the bug
Update code
```

### Scope

- Use a short noun identifying the subsystem: `auth`, `api`, `db`, `ui`, `cli`, `config`
- Scope is required for `feat` and `fix` types
- Scope is optional for `docs`, `chore`, `ci`, `build`, `style`
- Never use file names or paths as scope

### Body

- Separate from subject with a blank line
- Wrap at 80 characters
- Explain _why_ the change was made, not _what_ changed (the diff shows that)
- Reference related issues with `Refs: #123` or `Closes: #456`

### Footer

- `BREAKING CHANGE: <description>` for any backward-incompatible change
- BREAKING CHANGE footer is mandatory when the change alters public API signatures, removes or renames exported symbols, changes configuration schema, modifies database schema in non-additive ways, or changes CLI flags/arguments
- Place each footer on its own line
- Use `Refs:` or `Closes:` for issue references

```
feat(api)!: require authentication on /users endpoint

All /users requests now require a valid Bearer token. Anonymous
access was a security oversight from the initial prototype.

BREAKING CHANGE: GET /users returns 401 without Authorization header
Closes: #89
```

## Branch Naming

### Format

```
<type>/<ticket-or-slug>
```

### Prefixes

| Prefix      | Purpose                    |
| ----------- | -------------------------- |
| `feat/`     | New feature                |
| `fix/`      | Bug fix                    |
| `chore/`    | Maintenance, tooling       |
| `docs/`     | Documentation              |
| `refactor/` | Code restructuring         |
| `test/`     | Test additions/changes     |
| `ci/`       | CI/CD pipeline changes     |
| `release/`  | Release preparation        |
| `hotfix/`   | Production emergency fixes |

### Rules

- Use kebab-case for the slug portion: `feat/add-jwt-rotation`
- Include ticket number when available: `fix/PROJ-342-null-query`
- Keep branch names under 50 characters
- Never use personal names or dates in branch names

## Merge and Squash Policy

### When to Squash

- Feature branches with WIP/fixup commits that add noise
- Branches where intermediate commits do not represent meaningful standalone states

### When to Merge (No Squash)

- Branches with clean, logical commit history where each commit is meaningful
- Release branches
- Branches with co-authored commits that should preserve attribution

### Merge Commit Format

```
Merge pull request #<number> from <branch>

<PR title following conventional commit format>
```

### Pull Request Requirements

- PR title follows conventional commit format: `type(scope): description`
- PR body references related issues
- All CI checks pass before merge
- At least one approval for non-trivial changes

## Commit Hygiene

- One logical change per commit — do not mix refactoring with feature work
- Never commit generated files, build artifacts, or secrets
- Ensure the repository builds and tests pass at every commit (bisectability)
- Use `git add -p` to stage only relevant hunks when a working tree has mixed changes
- Rebase feature branches onto the target branch before merging to maintain linear history
