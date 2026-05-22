# Merge Discipline

Stacked PRs land bottom-up from the base perspective: merge the root PR first, then the next child, then the leaf.

## Rules

- Require parent PR checks before merging a child.
- Merge only one stack PR at a time.
- After each merge, fetch, rebase the next child onto the updated base, push with lease, and retarget the child PR.
- Delete remote branches only through provider-confirmed merge or explicit cleanup.
- Delete local branches only when `git branch --merged <base>` proves they are merged.

## Root Merge

```bash
gh pr merge <root-pr> --merge --delete-branch
git fetch origin --prune
```

## Promote Next Child

```bash
git switch <child-branch>
git rebase origin/main
git push --force-with-lease origin <child-branch>
gh pr edit <child-pr> --base main
```

Then validate and merge that child.

## Cleanup

```bash
git switch main
git pull --ff-only origin main
git fetch --prune origin
git branch --merged main
git branch -d <merged-stack-branch>
```

Never use `git branch -D` for stack cleanup unless the user explicitly asks to delete an unmerged branch after reviewing the risk.

## Stop Conditions

- Parent PR is not merged.
- Required checks are failing or pending.
- Provider reports branch protection failure.
- Rebase conflict occurs after parent merge.
- Local branch is not listed by `git branch --merged <base>`.

Report the stopped branch and next safe command.
