# DFG-GOV-01 — Dataset Governance Contract Reconciliation

- **Status:** verified_complete
- **Owner:** Charlie Boswell
- **Authorized:** 2026-08-23
- **Accepted:** 2026-08-23
- **Repository base:** `63c213f4b88454eed360f02b150a2855f340aa1b`
- **Reviewed head:** `1e6d5b62f970a7ba3141ca35fc931fb75c0ec056`
- **Merged PR:** `#45`
- **Merge commit:** `364dcb9443c938ccab28dec250d6768d70e30a7f`

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

Hosted verification at reviewed head `1e6d5b62f970a7ba3141ca35fc931fb75c0ec056`:

- Test Suite run `32642640068`: success
- Docker Build and Push run `32642640118`: success
- Security Scanning run `32642640236`: success

Bounded local verification:

```bash
python scripts/validate_dfg_gov_01.py docs/plans/DFG_GOV_01/fixtures/valid.json
python -m unittest -v tests.test_dfg_gov_01
bash doc/system/BUILD.sh
```

## Next gate

DFG-GOV-01 is closed as verified complete. The candidate contract remains
unadmitted. A separate owner-authorized HFX-14E.3/DFG package is required for
consumers, persistence, APIs, or runtime behavior; this closeout grants none of
those authorities and advances no later phase automatically.
