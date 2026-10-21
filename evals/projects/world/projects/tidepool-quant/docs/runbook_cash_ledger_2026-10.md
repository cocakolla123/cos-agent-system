# Runbook: cash ledger fix and release (2026-10)

## Dry run (2026-10-05, read only)
Done. Output matched expectations.

## Order of operations
1. `scripts/repair_ledger.py --step curve --apply`. Check the printed equity curve.
2. `scripts/repair_ledger.py --step ladder --apply`.
3. `scripts/repair_ledger.py --step ack --apply --acked-by <name>`.

Record each step in docs/ops-log.md when it is done.
