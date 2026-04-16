---
name: adaptive-thinking-control
type: rule
description: >
  Controls reasoning depth on Claude Opus 4.7 via prompt-level directives,
  replacing the removed fixed-budget Extended Thinking feature. Opus 4.7 uses
  adaptive thinking — the model chooses whether to think at each step — so
  the lever moved from a numeric budget_tokens parameter to specific prompt
  phrases that nudge depth up or down. Covers the deeper-reasoning cue,
  the lower-latency cue, anti-patterns (setting budget_tokens on 4.7,
  assuming the model will always think by default), and effort-level
  interactions. Use this rule when prompting Opus 4.7 for tasks where
  reasoning depth or latency materially affects the outcome. Triggers on:
  "adaptive thinking", "thinking budget", "extended thinking", "budget_tokens",
  "Opus 4.7 thinking", "make Claude think harder", "make Claude faster",
  "reasoning depth", "latency vs reasoning", "xhigh effort", "max effort".
metadata:
  version: 1.0.0
  scope: global
  applies_to:
    languages: ["*"]
  category: development
  tags: [opus-4-7, adaptive-thinking, prompting, effort, extended-thinking]
  difficulty: beginner
---

# Adaptive Thinking Control

Rules for controlling reasoning depth on Claude Opus 4.7, which replaced fixed-budget Extended Thinking with adaptive thinking. The model now decides whether to think at each step — so the lever moved from a numeric `budget_tokens` parameter to prompt-level directives. This rule documents the directives that actually work and the anti-patterns that silently fail.

## What Changed in Opus 4.7

Opus 4.7 does not support Extended Thinking with a fixed `budget_tokens` value. The adaptive-thinking mechanism makes thinking optional per step: the model may reason deeply on a hard sub-task and respond immediately on a trivial one in the same conversation. There is no dial to set a global depth; there are prompt phrases that bias the choice.

This applies to both direct Anthropic API usage and to Claude Code, where effort levels (`low`/`medium`/`high`/`xhigh`/`max`) set the ceiling for reasoning budget but do not force the model to think when it judges thinking unnecessary.

## Deeper-Reasoning Cue

When the task is harder than it looks or a shallow pass will miss edge cases, prompt with:

> "Think carefully and step-by-step before responding; this problem is harder than it looks."

Place this phrase **early** in the first-turn prompt, alongside intent and constraints. Opus 4.7 follows instructions literally, so late cues compete with the momentum of a direct-response default.

**When to apply:**

- Architecture design where trade-offs span multiple dimensions
- Debugging across distributed systems, race conditions, or subtle state bugs
- Refactors that touch many call sites and need AST-level reasoning
- Formal reasoning: proofs, security analysis, invariant derivation
- Any task where the correct answer is non-obvious from surface reading

## Lower-Latency Cue

When the task is mechanical or time-sensitive, prompt with:

> "Prioritize responding quickly rather than thinking deeply. When in doubt, respond directly."

**When to apply:**

- Rote edits (renames, imports, boilerplate)
- Lookups and retrievals where the answer is in the context already
- Bulk or parallel sub-agent tasks where latency compounds
- Status checks and polling loops
- Conversational or confirmatory turns

## Anti-Patterns

**Do not set `budget_tokens` on Opus 4.7.** Code that still sends `thinking={"type": "enabled", "budget_tokens": N}` against Opus 4.7 will fail or be ignored depending on SDK version. Remove the parameter; rely on prompt-level control instead.

**Do not assume Opus 4.7 will always think.** Under 4.6, Extended Thinking was often on by default for agentic tasks. Under 4.7, an ambiguous prompt can produce a terse direct answer. If depth matters, state it explicitly.

**Do not stack cues.** Prompting "Think carefully and step-by-step, but also respond quickly" confuses the adaptive-thinking choice. Pick one direction per prompt.

**Do not rely on emoji, bold, or repetition to "force" thinking.** 4.7's literal instruction following means it takes the phrasing at face value. The deeper-reasoning cue above is calibrated; paraphrases that sound equivalent may not elicit the same behavior.

## Effort-Level Interactions

Claude Code's `/effort` command sets the reasoning ceiling, not a floor. Adaptive thinking operates within that ceiling.

| Effort   | Use when                                                                              |
| -------- | ------------------------------------------------------------------------------------- |
| `low`    | Trivial edits, latency-critical loops                                                 |
| `medium` | Single-file changes, low-stakes refactors                                             |
| `high`   | Cost-sensitive or concurrent sessions where you accept slightly shallower reasoning   |
| `xhigh`  | **Default.** Best for most coding and agentic work                                    |
| `max`    | Genuinely hard novel problems only — diminishing returns, overthinking risk           |

The deeper-reasoning cue has the largest effect at `xhigh` and `max`. Below `high`, the effort ceiling dominates and the cue is advisory.

## First-Turn Discipline

Opus 4.7 reasons more when the task is specified completely up front: intent, constraints, acceptance criteria, and file paths in one message. Every additional user turn that adds context adds reasoning overhead and fragments the adaptive-thinking choice across turns.

Batch context into the first message. Reserve subsequent turns for corrections and scope changes, not initial specification.

## Migration from Opus 4.6

If a prompt, agent, or skill previously depended on verbose Opus 4.6 reasoning by default:

1. Add the deeper-reasoning cue to the first-turn prompt where depth is load-bearing.
2. Remove any `budget_tokens` values from Anthropic SDK calls targeting Opus 4.7.
3. For agent orchestrators, state sub-task independence explicitly when parallel dispatch is required — 4.7's judicious delegation default can serialize otherwise.
4. Review length expectations: 4.7 is less default-verbose, so requests for structured long-form output may need an explicit length directive.

## Related

- `~/.claude/CLAUDE.md` — global Opus 4.7 prompt patterns and effort-level defaults
- `rules/token-efficiency/RULE.md` — general tool-usage token discipline (complements but does not replace this rule)
- `skills/prompt-lab/` — prompt-pattern catalog including CoT variants
