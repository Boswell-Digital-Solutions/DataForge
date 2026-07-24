# Canonical Telemetry CP2 Threat Model

**Scope:** DataForge search producer, SDK private SQLite recovery, authenticated
canonical HTTP ingress, and isolated PostgreSQL telemetry pool.

**Out of scope:** Forge_Command collector ingress, OTLP, cross-language SDKs,
CP3 correlation, and all pre-v1/legacy paths.

## Assets and trust boundaries

| Asset | Boundary | Control |
| --- | --- | --- |
| DataForge API key | Producer process → HTTPS/loopback HTTP | Dedicated header-only key; never written to spool, status, receipts, or logs |
| Canonical event bytes | Producer memory → private SQLite → HTTPS → PostgreSQL | Strict `ForgeEvent.v1`, 65,536-byte ceiling, RFC 8785 digest, mode `0700` parent/mode `0600` file |
| Producer identity | HTTP auth boundary | API-key metadata must exactly bind service, environment, tenant, and `telemetry:write` |
| Delivery truth | SQLite/HTTP/PostgreSQL | Local commit is only `queued`; only content-bound `inserted`/`exact_replay` is persisted |
| Business DB capacity | FastAPI dependency boundary | Separate login and engine, pool 2/overflow 0, finite DB timeouts, 20/s plus 40 burst pre-checkout budget |
| Canonical evidence | PostgreSQL table/function/RLS | NOLOGIN group role, role-scoped policies, `SELECT`/`INSERT` only, no update/delete |

## Threats and dispositions

| Threat | Disposition |
| --- | --- |
| Unauthenticated remote producer | Existing DataForge API-key authentication rejects it before event authorization. |
| Valid key claiming another subject | Exact service/environment/tenant binding fails closed. |
| AuthorForge content sent to generic telemetry | `service_name=authorforge` is always forbidden; only the separate closed analytics envelope is allowed. |
| Replay with the same ID and bytes | Returns `exact_replay` and preserves original sink time. |
| Replay with the same ID and changed bytes | Returns `event_identity_conflict`; the spool quarantines it. |
| API key or upstream error reaches disk/logs | Spool schema has no credential/URL/header/raw-error field; public errors and logs use stable codes. Canary tests inspect persisted bytes and health output. |
| Symlink/path substitution | SDK rejects a symlink database or immediate parent, non-owner paths, and any group/other permission bits. |
| Another local user reads queued events | Immediate directory must be mode `0700`; database is mode `0600`. Residual risk: host/root compromise can read canonical telemetry because the spool is not application-encrypted. |
| Shared SQLite file across processes | Unsupported and documented; each producer process requires a unique path. |
| Disk/queue exhaustion | Fixed 512-entry/32 MiB budget rejects newest input truthfully; no unbounded memory mirror exists. |
| Corrupt local row blocks recovery | The row quarantines with a value-free code; later healthy rows continue. |
| Crash or lost acknowledgement causes duplicate replay | Expired inflight and post-send uncertainty become `indeterminate`; automatic drain skips them until explicit duplicate-risk acceptance. |
| Downstream outage causes hot retry | Per-entry attempts/backoff are finite; three consecutive failures open a 15-second circuit and stop the batch. |
| Cancellation hides live work | SDK capacity remains occupied until the one drain worker actually completes; finite shutdown reports timeout instead of false success. |
| Telemetry exhausts business DB | The route has no `get_db()` fallback. A distinct login uses a separate 2/0 pool; a disposable PostgreSQL proof exhausts it without changing business-pool checkout state. |
| Telemetry login is overprivileged | Startup preflight rejects the business username, missing group membership, superuser, `BYPASSRLS`, or wrong application name. |
| Telemetry reads or mutates business data | Migration grants only schema usage, canonical-table `SELECT`/`INSERT`, and required functions. PostgreSQL proof denies business-table read and canonical delete. |
| Request flood consumes telemetry pool | After API-key authentication, the token bucket rejects above 20 events/s and burst 40 before connection checkout; unauthenticated requests cannot spend the producer budget. Pool checkout/connect/statement/lock/idle transaction timeouts are finite. |
| Rollback deletes evidence | Writer kill switch and spool-path rollback are non-destructive. The CP2 migration downgrade revokes grants/policies but retains the group role, login roles, table, and rows. |

## Residual risks and explicit non-decisions

- SQLite event bytes are protected by the producer host's filesystem boundary,
  not application-level encryption. Only already-approved minimized canonical
  events may enter the pilot.
- The rate budget is per process. Deployment replica count therefore remains
  part of the operator's total sink budget.
- A drain timeout cannot terminate an already-running blocking HTTP call.
  Capacity remains charged and shutdown reports the unresolved state.
- Forge_Command's loopback bridge does not yet bind an external process
  cryptographically to its claimed telemetry subject. It is not selected as
  CP2 ingress and receives no canonical event route in this checkpoint.
- Production enablement remains a separate operator action after the proof
  packet is accepted. No repository default enables the writer or spool.
