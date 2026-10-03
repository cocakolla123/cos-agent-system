# Eval run baseline-v1

- instructions: `instructions/extract_v1.md` (sha256 `53469b6a54bb…`)
- model arg: (default) · cli: 2.1.269 (Claude Code)
- date: 2026-10-03

## dev (18 scenarios)

| metric | value |
|---|---|
| precision | 0.6842 |
| recall | 0.7647 |
| f1 | 0.7222 |
| due_accuracy | 1.0 |
| citation_accuracy | 1.0 |
| direction_accuracy | 1.0 |
| grouping_accuracy | 1.0 |
| invented_items | 0 |
| duplicate_failures | 0 |
| isolation_violations | 3 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 28352 |
| mean_cost_usd | 0.531 |
| total_cost_usd | 9.5585 |
| injection resisted | 2/2 |

per category F1: approval_action 1.00, blocked 1.00, conflict_stale 0.67, deadline_change 0.50, dedupe_cross_surface 0.50, injection 1.00, isolation 0.40, mixed_noise 1.00, no_invention 1.00, owed_to_user 0.00, satisfied 1.00, user_owes 1.00

## test (18 scenarios)

| metric | value |
|---|---|
| precision | 0.8333 |
| recall | 1.0 |
| f1 | 0.9091 |
| due_accuracy | 1.0 |
| citation_accuracy | 1.0 |
| direction_accuracy | 1.0 |
| grouping_accuracy | 1.0 |
| invented_items | 1 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 26482 |
| mean_cost_usd | 0.5066 |
| total_cost_usd | 9.1186 |
| injection resisted | 1/1 |

per category F1: approval_action 1.00, blocked 0.67, conflict_stale 0.67, deadline_change 1.00, dedupe_cross_surface 1.00, injection 1.00, isolation 1.00, mixed_noise 1.00, no_invention 1.00, owed_to_user 1.00, satisfied 0.00, user_owes 1.00
