---
name: ai-builder
type: preset
description: >
  AI development toolkit for building, testing, and optimizing LLM-powered systems in Claude
  Code. Bundles agent development, prompt engineering, GPU and inference optimization, RAG
  pipeline auditing, MCP server conversion, and notebook generation into a single install.
  Covers the full AI workflow from designing prompts through building agents, optimizing GPU
  utilization, auditing retrieval quality, and extending tool integrations. Use this preset
  when setting up an AI development environment, machine learning toolkit, or LLM tools
  workspace. Relevant for agent development, MCP development, RAG pipeline construction,
  and inference optimization workflows.
metadata:
  version: 1.0.0
preset:
  packages:
    skills:
      - name: agent-builder
      - name: prompt-lab
      - name: gpu-optimizer
      - name: rag-auditor
      - name: mcp-to-skill
      - name: notebooklm
  compatibility:
    platforms: [darwin, linux]
---

# AI Builder

End-to-end toolkit for developing, optimizing, and validating AI-powered systems.

## Included Skills

| Skill         | Purpose                                    | Domain               |
| ------------- | ------------------------------------------ | -------------------- |
| agent-builder | Custom agent creation and orchestration    | Agent development    |
| prompt-lab    | Prompt engineering, testing, and iteration | Prompt design        |
| gpu-optimizer | GPU/CUDA performance tuning                | Inference optimization |
| rag-auditor   | RAG pipeline quality and retrieval auditing | Retrieval systems    |
| mcp-to-skill  | Convert MCP servers into installable skills | Tool integration     |
| notebooklm   | Notebook generation for exploration        | Documentation        |

## Workflow

1. **Design** — Use `prompt-lab` to engineer, test, and iterate on prompts. Establish
   baseline performance before building higher-level abstractions.
2. **Build** — Use `agent-builder` to create custom agents that compose prompts, tools,
   and orchestration logic into autonomous workflows.
3. **Optimize** — Use `gpu-optimizer` to profile and tune GPU/CUDA utilization for
   inference workloads. Reduce latency and cost per request.
4. **Audit** — Use `rag-auditor` to evaluate retrieval quality, chunk relevance, and
   end-to-end RAG pipeline accuracy. Catch retrieval drift before it reaches users.
5. **Extend** — Use `mcp-to-skill` to convert existing MCP servers into reusable skills,
   expanding the agent's tool surface without writing integrations from scratch.
6. **Document** — Use `notebooklm` to generate notebooks that capture experiments,
   results, and architectural decisions.

## Choosing the Right Skill

| Situation                                        | Skill         |
| ------------------------------------------------ | ------------- |
| Writing or refining a system prompt               | prompt-lab    |
| Building multi-step agent workflows               | agent-builder |
| Slow inference or high GPU memory usage           | gpu-optimizer |
| Poor retrieval relevance or hallucination spikes  | rag-auditor   |
| Wrapping an MCP server as a portable skill        | mcp-to-skill  |
| Creating exploratory or explanatory notebooks     | notebooklm   |

## When to Use

- Setting up an AI or LLM development environment from scratch.
- Building custom agents that compose prompts, retrieval, and tool use.
- Optimizing GPU utilization and inference latency for deployed models.
- Auditing RAG pipelines for retrieval quality and grounding accuracy.
- Converting MCP servers into skills for broader distribution.
- Prototyping AI workflows that span prompt design through deployment.
