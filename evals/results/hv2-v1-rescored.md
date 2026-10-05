# Eval run hv2-v1

- instructions: `instructions/extract_v1.md` (sha256 `53469b6a54bb…`)
- model arg: (default) · cli: 2.1.289 (Claude Code)
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
| invented_items | 1 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 7232 |
| mean_cost_usd | 0.0809 |
| total_cost_usd | 0.8087 |
| injection resisted | 1/1 |

per category F1: ambiguous_owner 1.00, cancellation 1.00, conflict 0.80, injection 1.00, injection_benign 1.00, messy 1.00, unsupported_deadline 1.00

## test (36 scenarios)

| metric | value |
|---|---|
| precision | 0.9667 |
| recall | 1.0 |
| f1 | 0.9831 |
| due_accuracy | 0.9655 |
| citation_accuracy | 1.0 |
| direction_accuracy | 1.0 |
| grouping_accuracy | None |
| invented_items | 1 |
| duplicate_failures | 0 |
| isolation_violations | 0 |
| format_errors | 0 |
| parse_failures | 0 |
| median_latency_ms | 8019 |
| mean_cost_usd | 0.0809 |
| total_cost_usd | 2.9132 |
| injection resisted | 7/7 |

per category F1: ambiguous_owner 1.00, cancellation 1.00, conflict 1.00, injection 0.93, injection_benign 1.00, messy 1.00, unsupported_deadline 1.00
