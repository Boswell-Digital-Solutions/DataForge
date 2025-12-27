# DataForge Security Enforcement

DataForge is a **protected service** within the Forge Ecosystem. It enforces authentication, authorization, and key lifecycle rules defined by Forge Command.

---

## Authentication Model

### Accepted Authentication Methods

DataForge accepts requests authenticated by:

1. **Active API Keys**
   - Stored hashed in the service database
   - Issued and rotated by Forge Command
   - Validated on every request

2. **Emergency Operations Key**
   - Provided via `X-Emergency-Key` header
   - Intended for disaster recovery only
   - All usage is audit-logged

No other authentication methods are permitted.

---

## Key Lifecycle Rules

### Rotation
- API keys rotate every 30 days
- Old keys remain valid for 7 days post-rotation
- Revocation is delayed to prevent outages

### Kitchen Hours
- Automated rotations are blocked between 10:00–22:00 local time
- Manual rotation requires explicit authorization
- Emergency key bypasses time restrictions

---

## Authorization Boundaries

DataForge enforces:
- Route-level permission checks
- Separation between runtime access and administrative access
- Dedicated `ROTATION_ADMIN_TOKEN` for key issuance endpoints

The rotation token **cannot** be used for normal API operations.

---

## Storage & Handling

- API keys are never stored in plaintext
- Hashing uses approved cryptographic primitives
- Key prefixes may be logged for diagnostics
- Full keys must never appear in logs or error traces

---

## Failure & Recovery

### If Authentication Fails
- Return explicit 401/403 responses
- Do not leak internal state
- Do not auto-regenerate keys

### Disaster Recovery
- Emergency key restores access
- Forge Command re-establishes normal credentials
- All recovery actions are auditable

---

## Audit Guarantees

DataForge guarantees:
- Deterministic authentication behavior
- Verifiable key provenance
- Tamper-evident logs for security events

---

## Absolute Rule

> **DataForge never trusts client applications.
> It only trusts cryptographic proof and Forge Command authority.**
