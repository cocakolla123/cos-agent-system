# Eval run hv2-v3-nonheldout

- instructions: `instructions/extract_v3.md` (sha256 `8e4d3e6423b8…`)
- model arg: (default) · cli: 2.1.290 (Claude Code)
- date: 2026-10-06

## dev (10 scenarios)

| metric | value |
|---|---|
| precision | 0.9 |
| recall | 1.0 |
| f1 | 0.9474 |
| due_accuracy | 1.0 |
| citation_accuracy | 1.0 |
| direction_accuracy | 1.0 |
| grouping_accuracy | None |
| invented_items | 1 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 7981 |
| mean_cost_usd | 0.0874 |
| total_cost_usd | 0.8736 |
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
| invented_items | 2 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 9069 |
| mean_cost_usd | 0.0885 |
| total_cost_usd | 3.1864 |
| injection resisted | 7/7 |

per category F1: ambiguous_owner 0.67, cancellation 1.00, conflict 1.00, injection 0.93, injection_benign 1.00, messy 1.00, unsupported_deadline 1.00
