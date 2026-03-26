# Wanted — Contribution Opportunities

Missing skill domains, requested agents, and infrastructure improvements. Pick one and open a PR.

---

## Skills

| Domain | Suggested Name | Difficulty | Description |
|--------|---------------|------------|-------------|
| Kubernetes | `kubernetes-ops` | advanced | Cluster operations, pod debugging, manifest validation, rollout management via kubectl |
| Terraform / IaC | `terraform-reviewer` | advanced | Plan review, state drift detection, module best practices, security policy checking |
| Docker | `dockerfile-optimizer` | intermediate | Multi-stage build optimization, layer caching, image size reduction, security scanning |
| Database Admin | `database-ops` | advanced | Schema design review, query plan analysis, connection pool tuning, backup verification |
| Mobile (React Native) | `react-native-dev` | intermediate | Component patterns, navigation setup, native module bridging, build troubleshooting |
| Mobile (Swift/iOS) | `swift-ios-dev` | intermediate | SwiftUI patterns, Core Data setup, App Store submission checklist, crash diagnostics |
| GraphQL | `graphql-reviewer` | intermediate | Schema design, resolver patterns, N+1 detection, pagination strategies |
| Observability | `observability-setup` | intermediate | Structured logging, distributed tracing, metric dashboards, alert rule design |
| API Design | `api-design-reviewer` | intermediate | REST/gRPC contract review, versioning strategy, pagination, error response design |
| Data Pipeline | `data-pipeline-reviewer` | advanced | ETL/ELT review, schema evolution, idempotency checks, backfill strategy |
| Accessibility | `accessibility-auditor` | intermediate | WCAG compliance checking, screen reader testing, keyboard navigation, color contrast |
| Performance | `web-perf-auditor` | intermediate | Core Web Vitals analysis, bundle size audit, lazy loading strategy, caching headers |

## Agents

| Name | Model | Difficulty | Description |
|------|-------|------------|-------------|
| `ci-debugger` | sonnet | advanced | Diagnose failing CI pipelines — parse logs, identify root cause, suggest fixes |
| `migration-planner` | opus | advanced | Plan multi-step database or framework migrations with rollback strategy |
| `onboarding-guide` | sonnet | intermediate | Walk new contributors through repo structure, dev setup, and first PR |
| `dependency-upgrader` | sonnet | intermediate | Analyze dependency update impact, generate migration plan, run compatibility checks |

## Infrastructure

| Item | Difficulty | Description |
|------|------------|-------------|
| MCP server for runtime discovery | advanced | Expose armory packages as MCP tools for agent-native search and recommendation |
| Web directory / catalog site | advanced | Static site generated from manifest.yaml with search, filters, and per-package pages |
| agentskills.io spec compliance | intermediate | Validate armory skills against the Agent Skills open standard and register qualifying packages |
| Eval runner | advanced | Execute eval cases against live Claude sessions and measure trigger accuracy |
| Package dependency graph | intermediate | Visualize complement relationships and suggest missing connections |

---

## How to Contribute

1. Pick an item from the tables above
2. Open an issue using the [Package Request](https://github.com/Mathews-Tom/armory/issues/new?template=package-request.yml) or [Feature Request](https://github.com/Mathews-Tom/armory/issues/new?template=feature-request.yml) template
3. Follow the [CONTRIBUTING.md](CONTRIBUTING.md) guidelines
4. Submit a PR with the skill evaluator scorecard (minimum 70%)

For design-level changes (new package types, adapter architecture, infrastructure), open an [RFC discussion](https://github.com/Mathews-Tom/armory/discussions/new?category=rfcs) first.
