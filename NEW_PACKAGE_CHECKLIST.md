# New Package Checklist

Follow this checklist every time you build a new package for the armory. Items are ordered by workflow phase — complete each phase before moving to the next.

**Definition files by type:**

| Type | Directory | Definition File |
| --- | --- | --- |
| Skill | `skills/` | `SKILL.md` |
| Agent | `agents/` | `AGENT.md` |
| Rule | `rules/` | `RULE.md` |
| Command | `commands/` | `COMMAND.md` |
| Hook | `hooks/` | `HOOK.md` |
| Utility | `utilities/` | `UTILITY.md` |
| Preset | `presets/` | `PRESET.md` |

---

## Phase 1: Planning

- [ ] **Define the scope** — what task domain does this package cover? Write one sentence.
- [ ] **Check for overlap** — search existing packages in `manifest.yaml` to confirm no existing package covers this domain. If overlap exists, decide: extend the existing package or create a new one with clear boundary documentation.
- [ ] **Identify the decision framework** — when should a user pick this package over alternatives? Draft a comparison table (e.g., "use X when..., use Y when...").
- [ ] **List prerequisites** — what binaries, packages, APIs, or services must be installed for the package to function?

## Phase 2: Structure

- [ ] **Create directory** — `{type-dir}/<package-name>/` with kebab-case name, max 64 characters.
- [ ] **Create definition file** (e.g., `SKILL.md`, `AGENT.md`, `HOOK.md`) with YAML frontmatter:
  ```yaml
  ---
  name: <package-name> # Must match directory name exactly
  description: <200-800 chars> # See description rules below
  metadata:
    version: 1.0.0
    category: development     # required
    tags: [keyword1, keyword2] # required
    difficulty: intermediate   # required
    phase: build               # optional — define/plan/build/verify/review/ship
  ---
  ```
- [ ] **Create `references/`** — add reference documents the package needs (setup guides, compatibility matrices, command references).
- [ ] **Create `templates/`** (optional) — add ready-to-use scripts. Make them executable (`chmod +x`).
- [ ] **Create `evals/cases.yaml`** — trigger accuracy tests (see Phase 4).

## Phase 3: Content — Definition File Body

Write the definition file body with these sections (in order):

- [ ] **Title and one-line summary**
- [ ] **When-to-use table** — comparison with related packages or tools (decision framework from Phase 1)
- [ ] **Triggers list** — explicit trigger phrases, grouped by synonym family
- [ ] **Prerequisites** — installation commands, verification steps
- [ ] **Core workflow** — numbered steps showing the end-to-end flow
- [ ] **Supported commands/operations** — grouped by category with examples
- [ ] **Unsupported operations** (if applicable) — what does NOT work, with alternatives
- [ ] **Common patterns** — 3-5 real-world usage patterns with complete code
- [ ] **Environment variables** (if applicable)
- [ ] **Troubleshooting** — common failure modes with diagnostic commands and fixes
- [ ] **Reference table** — links to all files in `references/`
- [ ] **Template table** — links to all files in `templates/` with descriptions
- [ ] **Rationalizations** (optional, recommended for review/quality/security skills) — table of common excuses agents use to skip steps, paired with factual rebuttals
- [ ] **Red Flags** (optional, recommended for multi-step workflows) — observable patterns indicating the skill isn't being followed correctly
- [ ] **Verification** (optional, recommended for skills with measurable outcomes) — checklist of concrete evidence requirements proving correct execution

## Phase 4: Eval Cases

Create `evals/cases.yaml` with:

- [ ] **2+ positive cases** (`trigger_expected: true`) — natural language prompts that should activate the package
- [ ] **2+ negative cases** (`trigger_expected: false`) — adjacent tasks the package should NOT handle
- [ ] Each case has a unique `id` (snake_case), a `prompt`, empty `fixtures: []`, and `rubric` items
- [ ] Validate: `uv run python scripts/validate_evals.py`

## Phase 5: Description Quality

The frontmatter description is the single highest-leverage field. Verify it contains:

- [ ] **Functional summary** — what the package does (first clause)
- [ ] **Key operations** — 3-5 specific capabilities listed
- [ ] **Trigger phrases** — 6+ phrases across 3+ synonym families (imperative and interrogative forms)
- [ ] **"Use when" clause** — concrete activation scenarios
- [ ] **Domain terms** — technical jargon users associate with this task
- [ ] **Length** — 200-800 characters (sweet spot for keyword density)
- [ ] **No angle brackets** (`<`, `>`)
- [ ] **No pushy language** ("always use", "you must", "never do")

## Phase 6: Validation

- [ ] **Regenerate manifest** — `uv run scripts/generate_manifest.py`
- [ ] **Validate evals** — `uv run python scripts/validate_evals.py`
- [ ] **Sync templates** (if using shared templates) — `uv run python scripts/sync_templates.py`
- [ ] **Run skill evaluator** — target score: 70%+ (Adequate), aim for 80%+ (Strong)
- [ ] **No CRITICAL findings** — name mismatch, missing frontmatter, broken file references
- [ ] **No HIGH findings** — missing workflow, zero trigger phrases, no error handling
- [ ] **Test locally** — `claude --add-dir {type-dir}/<package-name>` and verify activation

## Phase 7: Integration

- [ ] **Update README.md** — add the package to the appropriate catalog section
- [ ] **Update package count badge** in README.md header
- [ ] **Check self-containment** — no `../` references, no absolute paths outside package directory
- [ ] **No secrets** — no API keys, credentials, or internal URLs in any file

## Phase 8: PR Submission

- [ ] **Create feature branch** — `feat/<package-name>`
- [ ] **Commit** — small logical units, descriptive messages
- [ ] **Paste skill evaluator scorecard** in the PR description
- [ ] **Confirm CI passes** — manifest sync + eval validation

---

## Quick Reference: Minimum Scores for PR Acceptance

| Dimension                   | Minimum |
| --------------------------- | ------- |
| D1: Frontmatter Quality     | 3/5     |
| D2: Trigger Coverage        | 3/5     |
| D3: Structural Completeness | 3/5     |
| D4: Content Depth           | 3/5     |
| D5: Consistency & Integrity | 4/5     |
| D6: CONTRIBUTING Compliance | 4/5     |
| **Overall**                 | **70%** |

---

## Common Mistakes

| Mistake                           | Impact                                             | Fix                                                        |
| --------------------------------- | -------------------------------------------------- | ---------------------------------------------------------- |
| Description under 100 characters  | Package never activates — Claude cannot match intent | Expand to 200-800 chars with trigger phrases               |
| Directory name != frontmatter name | CRITICAL finding, PR rejected                      | Rename directory or frontmatter to match                   |
| No negative eval cases            | CI fails                                           | Add 2+ negative cases for adjacent-but-wrong tasks         |
| Referenced file does not exist    | D5 capped at 2/5                                   | Create all files before referencing them                   |
| Cross-package references (`../`)  | Breaks standalone distribution                     | Copy shared content via template sync system               |
| No troubleshooting section        | Users hit errors with no guidance                  | Add 3-5 common failure modes with fixes                    |
| Only imperative triggers          | Misses question-form queries                       | Add interrogative triggers ("is X better?", "how do I Y?") |
