---
name: refactor
type: command
description: 'Code simplification workflow that identifies and cleans recently modified
  files. Uses git diff to find changed files, analyzes cyclomatic complexity, detects
  duplicated logic, simplifies nested conditionals, extracts helpers only when justified,
  and verifies behavior preservation through tests. Triggers on: "/refactor", "clean
  up recent changes", "simplify this code", "reduce complexity", "clean before PR",
  "tidy up my code". Use this command when code works correctly but needs simplification
  before committing or merging.

  '
metadata:
  version: 1.0.0
  category: development
  tags: [refactoring, code-quality, simplification]
  difficulty: intermediate
  phase: review
command:
  syntax: /refactor [path]
  handler: inline
  dependencies: []
---
# Refactor Clean — Code Simplification Workflow

When the user invokes `/refactor [path]`, execute this workflow exactly.

## Step 1: Identify Targets

1. If a path is provided, scope to that file or directory.
2. If no path is provided, use `git diff --name-only HEAD~3` to find recently modified files.
   Fall back to `git diff --name-only main` if fewer than 3 commits on the branch.
3. Filter to source files only (exclude tests, configs, lockfiles, generated files).
4. Sort by modification recency — most recently changed first.
5. Present the file list to the user:

```markdown
## Files to clean

| #   | File          | Lines changed | Last modified |
| --- | ------------- | ------------- | ------------- |
| 1   | src/parser.py | +42 / -18     | 2 commits ago |
```

6. Proceed with all files unless the user narrows the scope.

## Step 2: Complexity Analysis

For each target file:

1. **Cyclomatic complexity**: Count decision points (if, elif, else, for, while, and, or,
   try/except, case/match, ternary). Flag functions with complexity > 10.
2. **Nesting depth**: Flag blocks nested > 3 levels deep.
3. **Function length**: Flag functions exceeding 40 lines.
4. **Parameter count**: Flag functions with > 5 parameters.

Report:

```markdown
### {filename} — Complexity

| Function   | Cyclomatic | Max depth | Lines | Params | Action needed |
| ---------- | ---------- | --------- | ----- | ------ | ------------- |
| parse()    | 14         | 5         | 62    | 3      | yes           |
| validate() | 6          | 2         | 18    | 2      | no            |
```

## Step 3: Duplication Detection

1. Scan target files for duplicated logic:
   - Identical or near-identical code blocks (>= 4 lines with <= 1 line difference).
   - Repeated patterns across functions (same control flow with different variable names).
   - Copy-pasted error handling blocks.
2. Group duplicates and identify the canonical location.
3. Do not flag intentional duplication (test setup, protocol implementations where
   abstraction would reduce clarity).

Report each duplicate group with file locations and line ranges.

## Step 4: Simplify Nested Conditionals

Apply these transformations where applicable:

1. **Guard clauses**: Convert `if condition: <long block> else: <short return>` to early
   return pattern.
2. **De-Morgan flattening**: Simplify `not (a and b)` to `not a or not b` when it
   improves readability.
3. **Lookup tables**: Replace `if/elif/elif/else` chains (>= 4 branches) with dictionary
   dispatch or match/case.
4. **Boolean simplification**: Replace `if x: return True else: return False` with
   `return x` (or `return bool(x)`).
5. **Null coalescing**: Replace `if x is not None: y = x else: y = default` with
   `y = x if x is not None else default` or language-specific null coalescing.

For each transformation:

- Show the before/after diff.
- Explain why the transformation improves the code.
- Verify the logic is equivalent.

## Step 5: Extract Helpers (Justified Only)

Extract a helper function only when ALL of these conditions hold:

1. The extracted block is called from >= 2 locations, OR
2. The extracted block is >= 15 lines AND has a clear single responsibility, AND
3. The extraction reduces the parent function's cyclomatic complexity by >= 3, AND
4. The helper's name is self-documenting (no `do_stuff`, `process_data`, `handle_thing`).

Do NOT extract when:

- The block is used once and is < 15 lines.
- Extraction would require passing > 4 parameters.
- The helper name would be less clear than the inline code.
- The block contains critical control flow (return, break, continue) that would
  require awkward signaling from the helper.

For each proposed extraction, state which conditions are met and justify.

## Step 6: Verify Behavior Preservation

1. Identify the test file(s) covering the modified code.
2. Run the existing test suite for the affected modules.
3. If tests pass, the refactoring is safe.
4. If no tests exist for the modified code:
   - Warn the user explicitly.
   - Write 2-3 characterization tests capturing current behavior before refactoring.
   - Run them to confirm green, then apply the refactoring, then re-run.
5. If tests fail after refactoring, revert the specific transformation that caused the
   failure and report it.

## Output Format

```markdown
## Refactor Clean Summary

**Scope:** `{path_or_git_diff_range}`
**Files analyzed:** {count}
**Files modified:** {count}

### Changes applied

| File      | Transformation             | Lines before | Lines after | Complexity delta |
| --------- | -------------------------- | ------------ | ----------- | ---------------- |
| parser.py | Guard clauses (3x)         | 62           | 48          | -4               |
| parser.py | Extract validate_header()  | —            | +12         | -3               |
| utils.py  | Deduplicate error handling | 28           | 16          | -2               |

### Skipped (justified)

| File   | Candidate          | Reason skipped                    |
| ------ | ------------------ | --------------------------------- |
| api.py | Extract auth block | Single use, 8 lines, name unclear |

### Test verification

- Tests run: {count}
- Tests passed: {count}
- Characterization tests added: {count}

### Net impact

- Total lines: {before} -> {after} ({delta})
- Avg cyclomatic complexity: {before} -> {after}
- Functions simplified: {count}
- Helpers extracted: {count}
```

## Rules

- Every transformation must preserve exact external behavior. No functional changes.
- Run tests after each transformation, not just at the end.
- Do not rename public API symbols (function names, class names, parameter names used
  by callers) without explicit user approval.
- Do not change formatting style (quotes, trailing commas, etc.) — that is the formatter's job.
- Prefer fewer, higher-impact transformations over many trivial ones.
- If the code is already clean (complexity < 6, no duplication, reasonable nesting),
  report that and stop. Do not invent work.
