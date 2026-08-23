# DFG-GOV-01 — Dataset Governance Contract Reconciliation

**Status:** implemented_unverified  
**Owner:** Charlie Boswell  
**Authorized:** 2026-08-23  
**Repository base:** `63c213f4b88454eed360f02b150a2855f340aa1b`

This package is candidate-only and offline. It contains documentation, one
unadmitted schema, synthetic fixtures, a pure validator, and tests. It creates
no database table, API route, runtime consumer, provider connection, credential,
production-data path, deployment, or training authority.

The candidate ID is `dataforge.dataset_governance_candidate.v0`. It is absent
from the canonical registries and role matrix. Admission, persistence, and role
activation require later, separate decisions.

## Prerequisite proof

HFX-14E.2 passed CI run `32639020516` at reviewed head `35bc8f8` and merged as
`forge_contract_core` PR #70 at `d6a18a1`. See `source-lock.json`.

## Acceptance rules

1. Possession, ingestion, retrieval, or prior use never implies permission.
2. Retrieval, evaluation, and training eligibility are independent decisions.
3. Revocation or expiry invalidates affected eligibility and snapshots.
4. Similarity-group members cannot cross dataset splits.
5. Blocking contamination makes training ineligible.
6. Raw content and AuthorForge content-capable fields are forbidden.
7. Fixtures are synthetic and evidence remains digest/reference only.
8. No HFX-14E.3 role is activated.

## Verification

```bash
python scripts/validate_dfg_gov_01.py docs/plans/DFG_GOV_01/fixtures/valid.json
pytest -q tests/test_dfg_gov_01.py
bash doc/system/BUILD.sh
```

## Next gate

Owner review and acceptance. A separate HFX-14E.3/DFG package is required for
consumers, persistence, APIs, or runtime behavior.
