# ADR 0004 — Deterministic splits

Every source unit is assigned exactly once to `TRAIN`, `VALIDATION`, or `TEST`.
All members of one similarity group share one split, preventing duplicate
leakage. This creates no materialization or training authority.
