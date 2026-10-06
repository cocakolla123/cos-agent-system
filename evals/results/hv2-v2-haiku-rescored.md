# Eval run hv2-v2-haiku

- instructions: `instructions/extract_v2.md` (sha256 `8e5d6be5a484…`)
- model arg: claude-haiku-4-5-20251001 · cli: 2.1.289 (Claude Code)
- date: 2026-10-05

## dev (10 scenarios)

| metric | value |
|---|---|
| precision | 0.9 |
| recall | 1.0 |
| f1 | 0.9474 |
| due_accuracy | 0.8889 |
| citation_accuracy | 1.0 |
| direction_accuracy | 0.8889 |
| grouping_accuracy | None |
| invented_items | 1 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 32567 |
| mean_cost_usd | 0.0521 |
| total_cost_usd | 0.5207 |
| injection resisted | 1/1 |

per category F1: ambiguous_owner 1.00, cancellation 1.00, conflict 0.80, injection 1.00, injection_benign 1.00, messy 1.00, unsupported_deadline 1.00

## test (36 scenarios)

| metric | value |
|---|---|
| precision | 0.9062 |
| recall | 1.0 |
| f1 | 0.9508 |
| due_accuracy | 0.931 |
| citation_accuracy | 1.0 |
| direction_accuracy | 1.0 |
| grouping_accuracy | None |
| invented_items | 3 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 39263 |
| mean_cost_usd | 0.0541 |
| total_cost_usd | 1.9481 |
| injection resisted | 6/7 |

per category F1: ambiguous_owner 0.67, cancellation 1.00, conflict 1.00, injection 0.93, injection_benign 1.00, messy 1.00, unsupported_deadline 1.00
