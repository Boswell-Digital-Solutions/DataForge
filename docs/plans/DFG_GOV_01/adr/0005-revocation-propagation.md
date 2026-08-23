# ADR 0005 — Revocation propagation

A revoked or expired authorization invalidates every dependent eligible use and
affected snapshot. Replacement requires a new digest and qualification evidence.
No deletion process or database mutation is implemented here.
