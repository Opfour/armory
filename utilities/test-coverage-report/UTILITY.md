---
name: test-coverage-report
type: utility
description: >
  Summarizes test coverage for recently changed files by comparing git diffs against
  existing test files. Runs git diff to identify changed source files, checks whether
  corresponding test files exist, and prints a summary table. Exits non-zero if any
  changed source file lacks a test file. Use this utility when reviewing a branch or
  commit to verify that changed code has accompanying tests before merging.
metadata:
  version: 1.0.0
utility:
  runtime: python
  entry_point: scripts/coverage_report.py
  executable: true
---

# test-coverage-report

Check that recently changed source files have corresponding test files.

## Usage

```bash
# Check files changed in the last commit
python scripts/coverage_report.py

# Compare against a specific base ref
python scripts/coverage_report.py --base main

# Run in a specific repo
python scripts/coverage_report.py /path/to/repo
```

## Output Format

```
Changed files test coverage:

File                        Has Tests   Test File
src/auth.py                 yes         tests/test_auth.py
src/utils/parser.py         NO          -
lib/handler.ts              yes         lib/handler.test.ts

Summary: 2/3 files have tests (66.7%)
FAIL: 1 file(s) missing tests
```

The report exits with code 1 if any changed source file lacks a corresponding test file, making it suitable for CI gatekeeping.

## Test File Detection

The utility searches for test files matching these patterns:

| Source file | Test file patterns checked |
|-------------|--------------------------|
| `src/foo.py` | `test_foo.py`, `tests/test_foo.py`, `test/test_foo.py` |
| `src/foo.ts` | `foo.test.ts`, `foo.spec.ts`, `__tests__/foo.test.ts` |
| `src/foo.go` | `foo_test.go` (same directory) |

## Limitations

- Checks for test file existence only; does not measure line/branch coverage.
- Relies on naming conventions to match source files to test files.
- Requires git to be available and the path to be a git repository.
