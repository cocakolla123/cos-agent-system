# Eval run t108-v2-haiku

- instructions: `instructions/extract_v2.md` (sha256 `8e5d6be5a484…`)
- model arg: claude-haiku-4-5-20251001 · cli: 2.1.269 (Claude Code)
- date: 2026-10-03

## test (54 scenarios)

| metric | value |
|---|---|
| precision | 0.9375 |
| recall | 1.0 |
| f1 | 0.9677 |
| due_accuracy | 1.0 |
| citation_accuracy | 1.0 |
| direction_accuracy | 0.9778 |
| grouping_accuracy | 0.0 |
| invented_items | 0 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 1 |
| parse_failures | 0 |
| median_latency_ms | 33963 |
| mean_cost_usd | 0.0841 |
| total_cost_usd | 4.5414 |
| injection resisted | 3/3 |

per category F1: approval_action 1.00, blocked 1.00, conflict_stale 1.00, deadline_change 1.00, dedupe_cross_surface 1.00, injection 1.00, isolation 1.00, mixed_noise 1.00, no_invention 1.00, owed_to_user 1.00, satisfied 0.00, user_owes 1.00
