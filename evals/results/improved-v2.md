# Eval run improved-v2

- instructions: `instructions/extract_v2.md` (sha256 `8e5d6be5a484…`)
- model arg: (default) · cli: 2.1.269 (Claude Code)
- date: 2026-10-03

## dev (18 scenarios)

| metric | value |
|---|---|
| precision | 0.9444 |
| recall | 1.0 |
| f1 | 0.9714 |
| due_accuracy | 1.0 |
| citation_accuracy | 1.0 |
| direction_accuracy | 1.0 |
| grouping_accuracy | 0.6667 |
| invented_items | 0 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 26008 |
| mean_cost_usd | 0.5066 |
| total_cost_usd | 9.1189 |
| injection resisted | 2/2 |

per category F1: approval_action 1.00, blocked 1.00, conflict_stale 0.67, deadline_change 1.00, dedupe_cross_surface 1.00, injection 1.00, isolation 1.00, mixed_noise 1.00, no_invention 1.00, owed_to_user 1.00, satisfied 1.00, user_owes 1.00

## test (18 scenarios)

| metric | value |
|---|---|
| precision | 0.8235 |
| recall | 0.9333 |
| f1 | 0.875 |
| due_accuracy | 1.0 |
| citation_accuracy | 1.0 |
| direction_accuracy | 0.9286 |
| grouping_accuracy | 1.0 |
| invented_items | 0 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 27513 |
| mean_cost_usd | 0.4898 |
| total_cost_usd | 8.8173 |
| injection resisted | 1/1 |

per category F1: approval_action 1.00, blocked 0.50, conflict_stale 1.00, deadline_change 1.00, dedupe_cross_surface 1.00, injection 0.00, isolation 1.00, mixed_noise 1.00, no_invention 1.00, owed_to_user 1.00, satisfied 1.00, user_owes 1.00
