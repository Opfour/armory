---
name: terse-mode
type: preset
description:
  "Enforces terse, no-narration output from Claude Code. Bundles the prompt-context
  hook with a curated terse rules file that strips hedging, praise, soft language,
  meta-commentary, engagement phrases, and unsolicited offers from every response.
  Use this preset when you want action-only output without preambles, postambles,
  or trailing questions — code over prose, facts over hedging, stop at the information
  boundary. Triggers on: terse mode, concise output, minimal responses, quiet mode,
  no narration, brief output style.

  "
metadata:
  version: 1.0.0
  category: operations
  tags: [terse, concise, style, output, verbosity]
  difficulty: beginner
preset:
  packages:
    hooks:
      - { name: prompt-context }
  compatibility:
    platforms: [darwin, linux]
---

# Terse Mode

Enforces terse, action-only output from Claude Code by injecting strip-rules
into every prompt via the `prompt-context` hook.

## Included Packages

| Type | Package        | Role                                                  |
| ---- | -------------- | ----------------------------------------------------- |
| Hook | prompt-context | Injects rules as additionalContext on every user turn |

## Setup

After installing this preset, create `~/.claude/prompt-context.txt` with the
following content:

```text
Apply to your next response:
- No preamble, no postamble, no narration
- Strip hedging (think/perhaps/might/maybe/seems/likely/probably)
- Strip praise (great/perfect/excellent/amazing/fantastic)
- Strip soft language (would you like, if you'd prefer, you may want)
- Strip meta-commentary (let's, now we'll, moving on, next, first)
- Strip engagement (feel free, let me know, hope this helps, happy to)
- Strip offers (I can help with, shall we, should we)
- Strip terminal questions unless the user explicitly asked one
- After tool calls, stop. Do not summarize what just happened.
- Code over prose. Facts over hedging. Stop at the information boundary.
```

For project-specific overrides, place the file at `.claude/prompt-context.txt`
in the project root instead.

## Subagent Coverage

The hook covers main-agent output. Subagents (Explore, Plan, code-reviewer)
have isolated contexts that bypass `UserPromptSubmit`. To cover subagent
output, add an `outputStyle` to your `settings.json`:

```json
{
  "outputStyle": "concise"
}
```

Together, the hook handles main-agent prose and the output style handles
subagent prose.

## What This Replaces

Once installed, these sections in `CLAUDE.md` become redundant and can be
removed:

- "No preamble / no postamble / no narration" rules
- Lists of strip-words (hedging, praise, soft language, engagement)
- "Stop at information boundary" rules
- Self-check rituals ("scan your draft before sending")
- Compact Instructions sections (the hook survives compaction natively)

**Keep** in `CLAUDE.md`: honesty rules, technical precision rules,
code-quality rules, tool-use strategy, and imperative tone rules. These are
orthogonal to prose-style enforcement.

## Compliance

Realistic compliance ranges based on mechanism:

| Configuration                               | Compliance                         |
| ------------------------------------------- | ---------------------------------- |
| `CLAUDE.md` alone                           | ~50%                               |
| `CLAUDE.md` + `outputStyle`                 | ~70-80%                            |
| This preset (hook + `outputStyle` fallback) | ~85-95% main agent, ~70% subagents |

## Disabling

Rename or delete `~/.claude/prompt-context.txt`. The hook fails open —
the session reverts to default verbosity with no errors.
