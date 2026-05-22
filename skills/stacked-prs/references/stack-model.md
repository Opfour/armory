# Stack Model

A stack is an ordered set of branches where each branch depends on the branch before it.

```text
main
  -> feat/parser-core
      -> feat/parser-cache
          -> feat/parser-cli
```

## Sources Of Truth

Use these sources in order:

1. User-supplied explicit branch order.
2. Open PR metadata from the provider: `headRefName` and `baseRefName`.
3. `.stack-prs.yaml` when it exists.
4. Git ancestry only when it produces a single unambiguous parent chain.

Provider PR bases beat ancestry because review diff correctness depends on the hosted base ref, not only the local merge base.

## Inspection Commands

```bash
git rev-parse --show-toplevel
git status --porcelain
git branch --show-current
git for-each-ref --format='%(refname:short)' refs/heads
git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'
gh pr list --state open --json number,title,headRefName,baseRefName,state,url
```

For candidate parent checks:

```bash
git merge-base <branch> <candidate-parent>
git log --oneline <candidate-parent>..<branch>
```

## Required Model

Represent each stack entry with:

| Field | Meaning |
| --- | --- |
| `order` | 1-based position above the base branch |
| `branch` | Local head branch |
| `parent` | Base branch for review and rebase |
| `pr_number` | Provider PR number when one exists |
| `pr_state` | Provider state |
| `url` | Provider PR URL |
| `checks` | Latest known validation or provider check state |

## Stop Conditions

- No Git repository is detected.
- The stack has fewer than two dependent branches and the user asked for a normal PR.
- A requested branch does not exist locally.
- A branch appears more than once.
- Two candidate parents are equally plausible.
- Provider PR metadata contradicts explicit branch order.
- `.stack-prs.yaml` exists but fails schema validation.

When parent order is ambiguous, stop and request explicit branch order. Do not invent semantic relationships from branch names.
