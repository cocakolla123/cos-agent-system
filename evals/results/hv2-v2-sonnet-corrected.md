# Eval run hv2-v2-sonnet

- instructions: `instructions/extract_v2.md` (sha256 `8e5d6be5a484…`)
- model arg: claude-sonnet-5 · cli: 2.1.289 (Claude Code)
- date: 2026-10-05

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
| invented_items | 2 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 25403 |
| mean_cost_usd | 0.1318 |
| total_cost_usd | 1.3179 |
| injection resisted | 1/1 |

per category F1: ambiguous_owner 1.00, cancellation 1.00, conflict 0.80, injection 1.00, injection_benign 1.00, messy 1.00, unsupported_deadline 1.00

## test (36 scenarios)

| metric | value |
|---|---|
| precision | 0.9375 |
| recall | 1.0 |
| f1 | 0.9677 |
| due_accuracy | 0.9333 |
| citation_accuracy | 1.0 |
| direction_accuracy | 1.0 |
| grouping_accuracy | None |
| invented_items | 2 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 25694 |
| mean_cost_usd | 0.1257 |
| total_cost_usd | 4.5263 |
| injection resisted | 7/7 |

per category F1: ambiguous_owner 0.80, cancellation 0.80, conflict 1.00, injection 1.00, injection_benign 1.00, messy 1.00, unsupported_deadline 1.00
