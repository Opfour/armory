# Attribution — Code2Video

## Paper

**Title:** Code2Video: A Code-Centric Paradigm for Educational Video Generation
**Authors:** Anno Yanzhe Chen et al., Show Lab, National University of Singapore
**Venue:** NeurIPS 2025 Workshop on Deep Learning for Code (DL4C)
**arXiv:** https://arxiv.org/abs/2510.01174
**arXiv ID:** 2510.01174

## Upstream Repository

**URL:** https://github.com/showlab/Code2Video
**License:** MIT (see LICENSE in this directory)
**Pinned commit:** `f579f1e527f9d6684eb581853f8739b6b39f2914`

## What We Vendored

Prompt logic only — no code was copied. The three prompt templates in this directory
(`planner.md`, `coder.md`, `critic.md`) are adapted from the following upstream files,
with variable names and output schemas rewritten for Armory's `concept-to-video` schema:

| Armory file  | Upstream source(s)                                   |
|--------------|------------------------------------------------------|
| planner.md   | `prompts/stage1.py`, `prompts/stage2.py`             |
| coder.md     | `prompts/stage3.py`                                  |
| critic.md    | `prompts/stage4.py`                                  |

The upstream repo structures prompts as Python functions returning f-strings. We extracted
the prompt text, adapted variable names to match our schema, and reformatted as markdown
template files. No upstream Python code is included.

## What We Reimplemented

The following patterns are described in the paper and reimplemented independently from
scratch — no upstream code was copied:

- **Auto-fix loop** (paper §3.3): captures `manim render` stderr, extracts offending line
  range, calls the coder fixup prompt, patches the scene file in-place, retries up to N
  times. Our version lives in `scripts/render_video.py` and uses Python `subprocess`.
- **VLM critic loop** (paper §3.4): samples rendered frames, sends to a vision model with
  the critic prompt, receives anchor-based layout patches, re-renders. Our version calls
  Claude vision or Gemini via the existing Anthropic SDK — not Code2Video's custom wrapper.

## What We Skipped

The following upstream components were intentionally excluded:

- **MMMC benchmark** (`eval_TQ.py`, `eval_AES.py`): research evaluation harness, not
  relevant to a production skill. Would belong in `evals/skillsbench/` if ever adopted.
- **TeachQuiz metric**: research artifact — no end-user value.
- **IconFinder integration**: broke October 2025 per the upstream README. Replaced by the
  pluggable asset sourcing design in P4 (`scripts/fetch_assets.py`), which defaults to
  local SVG directories with IconFinder as an optional API-key-gated adapter.
- **Shell entry points** (`run_agent.sh`, `run_agent_single.sh`): our entry point is the
  SKILL.md workflow, not shell scripts.
- **3D ThreeDScene support**: excluded upstream and here; unreliable in headless containers.

## Re-sync Policy

These prompt templates are pinned to the commit SHA above. Re-sync opportunistically when
the upstream repo makes substantive prompt changes — do not auto-update. Compare diffs
against the pinned commit before merging any upstream changes.
