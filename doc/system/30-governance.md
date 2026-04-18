# Cache Governance
DOC_FETCH_CACHE_TTL=600
SEARCH_RESULTS_CACHE_TTL=300
EMBEDDING_RESULTS_CACHE_TTL=86400
SESSION_OAUTH_TOTP_CACHE_TTL=900
CORPUS_CURRENT_VERSION_CACHE_TTL=60
```

## Secrets Management

In production, secrets (`SECRET_KEY`, `JWT_SECRET_KEY`, `VOYAGE_API_KEY`, etc.) must not live in `.env` files committed to version control. Use:

- **ForgeCommand vault** — the canonical secrets source for Forge services
- **Docker secrets** — for container deployments
- **Kubernetes Secrets** — for k8s deployments (sealed or external-secrets operator)

LLM API keys are synced to DataForge from the ForgeCommand vault via the `/secrets` router. Services retrieve API keys through DataForge at runtime; keys never cross the IPC boundary in plaintext.

---
