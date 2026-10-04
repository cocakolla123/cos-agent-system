# Eval run t108-v2

- instructions: `instructions/extract_v2.md` (sha256 `8e5d6be5a484…`)
- model arg: (default) · cli: 2.1.269 (Claude Code)
- date: 2026-10-03

## test (54 scenarios)

| metric | value |
|---|---|
| precision | 0.8727 |
| recall | 1.0 |
| f1 | 0.932 |
| due_accuracy | 0.9583 |
| citation_accuracy | 1.0 |
| direction_accuracy | 0.9792 |
| grouping_accuracy | 1.0 |
| invented_items | 1 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 25905 |
| mean_cost_usd | 0.5047 |
| total_cost_usd | 27.2557 |
| injection resisted | 3/3 |

per category F1: approval_action 1.00, blocked 0.55, conflict_stale 0.75, deadline_change 1.00, dedupe_cross_surface 1.00, injection 1.00, isolation 1.00, mixed_noise 1.00, no_invention 1.00, owed_to_user 1.00, satisfied 1.00, user_owes 1.00
