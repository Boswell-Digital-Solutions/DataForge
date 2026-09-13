# BDS-DF-RF-001 — Receipt-to-Finding Knowledge Spine v0.1

**Title:** Receipt-to-Finding Knowledge Spine v0.1
**Owner (proposed, OD-01 open):** `Boswell-Digital-Solutions/DataForge`
**Lifecycle:** `proposed`
**Current authority:** Documentation placement and registration only
**Gate state:** WP-00 source lock and Board Review 1 packet complete; no gate opened yet, no Board ruling yet

## Why this plan exists

`BDS-RMCP-FC-GIR-v0.1` (Render/Forge_Command Governed Incident Repair) and `BDS-FPRS-v0.1` (Forge PR Steward) both cite `BDS-DF-RF-001` as the DataForge storage/envelope mapping their evidence receipts and findings depend on. As of 2026-09-13, that dependency had never been authored or registered anywhere. This plan is that authoring, started under an explicit Board ruling on `BDS-RMCP-FC-GIR-v0.1` ("author it as its own plan," 2026-09-13).

## Governing files

- `BDS_DF_RF_001_v0.1_WP00_SOURCE_LOCK_AND_BOARD_REVIEW_1_PACKET_2026-09-13.md` — code-verified current-state architecture (BugCheck's existing `Finding` lifecycle and its live DataForge persistence path; the admitted-but-dormant `bugcheck_finding.v1` contract; DataForge's existing `llm-intel/pending-records` intake as a reusable pattern; the `queued`/`persisted` semantics already defined in `forge-telemetry`), the proposed finding-candidate/BugCheck-finding boundary, and four open decisions for Board Review 1.

## Current decision

None yet — this plan has not been through its first Board Review. `OD-01` (canonical owner), `OD-02` (finding-candidate boundary: terminal vs. promotion-hook into `bugcheck_finding.v1`), `OD-03` (generalize the existing LLM-intel intake vs. build separately), and `OD-04` (correcting `BDS-RMCP-FC-GIR-v0.1`'s reference to a nonexistent `IssueQualificationReceipt.v1`) are all open.

Registration does not authorize schema publication or admission, runtime implementation, database changes, or any modification to BugCheck's existing findings machinery.
