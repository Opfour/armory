---
name: session-continuity
type: preset
description: 'Bundles the handoff skill, `/handoff` command, and opt-in Stop hook for maintaining `.docs/handoff.md` as a project-local session-continuity runbook. Covers refresh, greenfield scaffold, automatic Stop-event rewrite, authority-boundary enforcement, and 200-line cap. Triggers on: "session continuity", "handoff preset", "install handoff", "preserve session state", "cold-start primer", "resume checklist". Use this preset when teams want atomic install/uninstall of handoff capture across coding agents.'
packages:
  - skills/handoff
  - commands/handoff
  - hooks/handoff-on-stop
metadata:
  version: 0.1.0
  category: operations
  tags: [session-continuity, handoff, preset, runbook]
  difficulty: intermediate
  phase: ship
preset:
  packages:
    skills:
      - { name: handoff }
    commands:
      - { name: handoff }
    hooks:
      - { name: handoff-on-stop }
---

# Session Continuity

Installs the handoff workflow as one unit: manual refresh, greenfield scaffold, and opt-in Stop refresh.

## Included Packages

| Type | Package | Role |
| --- | --- | --- |
| Skill | handoff | Generates and maintains `.docs/handoff.md` |
| Command | handoff | Provides `/handoff` and `/handoff init` |
| Hook | handoff-on-stop | Refreshes on Stop when `.docs/handoff.md` already exists |

## Workflow

1. Install the preset.
2. In an opted-in project, run `/handoff init` once or create `.docs/handoff.md`.
3. Use `/handoff` any time session state should be refreshed.
4. On Stop, the hook refreshes only projects that already contain `.docs/handoff.md`.

## Opt-In Gate

The hook is project-gated by file presence. If `.docs/handoff.md` is absent, `handoff-on-stop` exits 0 and creates nothing. This prevents global installs from adding handoff files to unrelated repositories.

## Output

One project-local file:

```text
.docs/handoff.md
```

## Error Handling

| Problem | Resolution |
| --- | --- |
| Hook installed globally | File-presence gate prevents unwanted writes |
| Stop refresh fails | Hook logs and continues |
| Existing project lacks `.docs/` | `/handoff init` creates it |
| Handoff grows too large | Skill enforces 200-line cap |

