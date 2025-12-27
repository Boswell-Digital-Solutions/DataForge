# Security Policy

**DataForge — Service Enforcement Rules**

**Status:** Enforced
**Role:** Backend Service
**Authority:** Forge Command (for rotation tokens)
**Last Updated:** 2025-12-27

---

## Security Model

DataForge is a **backend service** that enforces authentication on all API requests. It accepts credentials but does not manage their lifecycle—rotation is coordinated by Forge Command.

---

## Authentication Enforcement

### Authorization Header Required

All API endpoints (except `/health`) require:

```
Authorization: Bearer <API_KEY>
```

Requests without valid credentials receive `401 Unauthorized`.

### Key Validation

DataForge validates keys against:
1. **Active key** — Current production key
2. **Overlap key** — Previous key during 7-day rotation window

Both are valid simultaneously during rotation overlap periods.

---

## Rotation Authority Model

DataForge recognizes three authorization paths:

| Header/Token | Purpose | Scope |
|--------------|---------|-------|
| `Authorization: Bearer <key>` | Normal API access | All endpoints |
| `X-Rotation-Admin-Token` | Key rotation operations | `/admin/rotate` |
| `X-Emergency-Ops-Key` | Emergency bypass | All (audit-logged) |

### Rotation Endpoint

```
POST /admin/rotate
X-Rotation-Admin-Token: <token>

{
  "new_key": "df_...",
  "overlap_days": 7
}
```

- Only Forge Command should call this endpoint
- Rotation requests outside kitchen hours (22:00–10:00) proceed normally
- Rotation during kitchen hours requires `X-Emergency-Ops-Key`

---

## Kitchen Hours Protection

DataForge enforces **kitchen hours blocking** on automated rotation:

| Time | Rotation Allowed |
|------|------------------|
| 22:00 – 10:00 | Yes (off-peak) |
| 10:00 – 22:00 | Blocked (kitchen hours) |

Emergency override:
```
X-Emergency-Ops-Key: <key>
```

All emergency overrides are audit-logged with timestamp and reason.

---

## Audit Requirements

DataForge logs all security-relevant events:

| Event | Logged Data |
|-------|-------------|
| Authentication failure | Timestamp, IP, endpoint |
| Key rotation | Timestamp, initiator, overlap period |
| Emergency override | Timestamp, reason, operator |
| Rate limit hit | Timestamp, IP, endpoint |

Logs are written to structured JSON format for analysis.

---

## Environment Variables

DataForge requires these secrets in its environment:

| Variable | Purpose |
|----------|---------|
| `DATAFORGE_API_KEY` | Active API key |
| `DATAFORGE_OVERLAP_KEY` | Previous key (during rotation) |
| `ROTATION_ADMIN_TOKEN` | Authorizes rotation requests |
| `EMERGENCY_OPS_KEY` | Break-glass override |

These are set by deployment infrastructure, not stored in code.

---

## Forbidden Patterns

DataForge code **must never**:

- Hardcode API keys in source
- Log credential values
- Accept unauthenticated requests (except `/health`)
- Skip key validation for "internal" requests
- Expose rotation tokens in API responses

---

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/api/v1/search` | 100/min |
| `/api/v1/documents` | 50/min |
| `/admin/*` | 10/min |

Exceeded limits return `429 Too Many Requests`.

---

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public issue
2. Email: security@boswelldigital.com
3. Include reproduction steps and impact assessment

---

## Related Documents

- [Forge Command SECURITY.md](../Forge_Command/SECURITY.md) — Credential authority policy
- [Systems Manual](../docs/FORGE_SYSTEMS_MANUAL.md) — Architecture reference

---

**Boswell Digital Solutions LLC**
