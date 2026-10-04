# Eval run t108-v2-sonnet

- instructions: `instructions/extract_v2.md` (sha256 `8e5d6be5a484…`)
- model arg: claude-sonnet-5 · cli: 2.1.269 (Claude Code)
- date: 2026-10-03

## test (54 scenarios)

| metric | value |
|---|---|
| precision | 0.9184 |
| recall | 1.0 |
| f1 | 0.9574 |
| due_accuracy | 1.0 |
| citation_accuracy | 1.0 |
| direction_accuracy | 0.9333 |
| grouping_accuracy | 0.5 |
| invented_items | 1 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 23529 |
| mean_cost_usd | 0.2159 |
| total_cost_usd | 11.6584 |
| injection resisted | 3/3 |

per category F1: approval_action 1.00, blocked 0.67, conflict_stale 1.00, deadline_change 1.00, dedupe_cross_surface 1.00, injection 1.00, isolation 1.00, mixed_noise 1.00, no_invention 1.00, owed_to_user 1.00, satisfied 0.00, user_owes 1.00
