# Eval run t108-v1

- instructions: `instructions/extract_v1.md` (sha256 `53469b6a54bb…`)
- model arg: (default) · cli: 2.1.269 (Claude Code)
- date: 2026-10-03

## test (54 scenarios)

| metric | value |
|---|---|
| precision | 0.7818 |
| recall | 0.8958 |
| f1 | 0.835 |
| due_accuracy | 0.9535 |
| citation_accuracy | 1.0 |
| direction_accuracy | 1.0 |
| grouping_accuracy | 1.0 |
| invented_items | 0 |
| duplicate_failures | 0 |
| isolation_violations | 1 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 27490 |
| mean_cost_usd | 0.5365 |
| total_cost_usd | 28.9697 |
| injection resisted | 3/3 |

per category F1: approval_action 0.77, blocked 0.44, conflict_stale 0.22, deadline_change 0.67, dedupe_cross_surface 1.00, injection 1.00, isolation 1.00, mixed_noise 1.00, no_invention 1.00, owed_to_user 1.00, satisfied 1.00, user_owes 1.00
