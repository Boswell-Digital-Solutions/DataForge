# §6 — PressForge Automation Schema

## 12. PressForge Automation Schema

> 11 new `pf_*` tables and column additions supporting the PressForge automation loop: governed job execution, GEO visibility tracking, social draftsets, prompt packs, agentic governance, config-as-code, and campaign outcomes.

### Overview

PressForge automation adds 11 tables to DataForge's existing 10 `pf_*` tables (journalists, campaigns, matches, pitches, outreach events, coverage, domain reputation, AI audit log, evidence items, retrieval runs). These support the NeuroForge automation runner's 9 tiered jobs.

All automation state persists here. NeuroForge is stateless beyond a run.

### New Tables (11)

#### `pf_automation_jobs` — Job Definitions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default uuid4 | Job definition ID |
| `job_key` | String(100) | NOT NULL, UNIQUE | e.g. `journalist_refresh`, `disinfo_scan` |
| `description` | Text | nullable | Human-readable job description |
| `cron_schedule` | String(100) | NOT NULL | Cron expression, e.g. `0 3 * * *` |
| `config` | JSONB | NOT NULL, default {} | Job-specific configuration |
| `enabled` | Boolean | NOT NULL, default true | Whether job should run |
| `tier` | Integer | NOT NULL, CHECK 1–4 | Job tier classification |
| `cost_class` | String(20) | NOT NULL, default "low" | CHECK: low, medium, high |
| `last_run_at` | DateTime | nullable | Last successful execution |
| `created_at` | DateTime | NOT NULL | Record creation timestamp |
| `updated_at` | DateTime | NOT NULL | Last modification timestamp |

**Relationships:** `runs → PfAutomationRun[]` (cascade delete)

#### `pf_automation_runs` — Execution Log

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Run instance ID |
| `job_id` | UUID | FK → pf_automation_jobs, CASCADE | Parent job |
| `job_key` | String(100) | NOT NULL, indexed | Denormalized for fast queries |
| `status` | String(20) | NOT NULL, CHECK | queued, running, success, failed, skipped |
| `started_at` | DateTime | nullable | Execution start |
| `ended_at` | DateTime | nullable | Execution end |
| `attempt` | Integer | NOT NULL, default 1 | Retry attempt number |
| `inputs_hash` | String(128) | nullable | Deterministic hash of inputs |
| `summary` | JSONB | nullable | Job-specific result summary |
| `error` | Text | nullable | Error message on failure |
| `cost_tokens` | Integer | nullable | Total LLM tokens consumed |
| `batch_id` | String(200) | nullable | Provider batch job ID |
| `provider_used` | String(50) | nullable | Which provider handled this run |
| `provider_latency_ms` | Integer | nullable | Provider response latency |
| `created_at` | DateTime | NOT NULL | Record creation timestamp |

**Relationships:** `job → PfAutomationJob`, `alerts → PfAutomationAlert[]`, `agent_logs → PfAgentLog[]`

#### `pf_automation_alerts` — Operator Alerts

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Alert ID |
| `run_id` | UUID | FK → pf_automation_runs, SET NULL | Originating run |
| `job_key` | String(100) | NOT NULL, indexed | Source job |
| `severity` | String(10) | NOT NULL, CHECK | info, warn, high |
| `title` | String(300) | NOT NULL | Alert headline |
| `detail` | Text | nullable | Extended description |
| `context` | JSONB | NOT NULL, default {} | Structured alert data |
| `dismissed` | Boolean | NOT NULL, default false | Operator acknowledged |
| `dismissed_by` | String(100) | nullable | Who dismissed |
| `dismissed_at` | DateTime | nullable | When dismissed |
| `created_at` | DateTime | NOT NULL | Alert timestamp |

#### `pf_automation_overrides` — Runtime Config Overrides

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Override ID |
| `job_key` | String(100) | NOT NULL, indexed | Target job |
| `override_config` | JSONB | NOT NULL | Merged over YAML baseline |
| `reason` | Text | NOT NULL | Governance audit trail |
| `expires_at` | DateTime | NOT NULL | Max 7 days from creation |
| `created_by` | String(100) | NOT NULL | Source identifier |
| `created_at` | DateTime | NOT NULL | Override creation timestamp |

#### `pf_agent_logs` — Agentic Governance Audit (Append-Only)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Log entry ID |
| `run_id` | UUID | FK → pf_automation_runs, SET NULL | Associated run |
| `job_key` | String(100) | NOT NULL, indexed | Source job |
| `action_type` | String(100) | NOT NULL, CHECK | Decision type (see below) |
| `input_state` | JSONB | NOT NULL, default {} | State before decision |
| `decision_rationale` | Text | NOT NULL | Why this decision was made |
| `output_action` | JSONB | NOT NULL, default {} | Action taken |
| `risk_flags` | JSONB | NOT NULL, default {} | Risk assessment metadata |
| `accepted` | Boolean | nullable | null until human responds |
| `accepted_by` | String(100) | nullable | Human reviewer |
| `created_at` | DateTime | NOT NULL | Decision timestamp |

**Action types (CHECK):** `route_priority`, `suggest_config`, `widen_query`, `escalate_human`, `auto_pause`, `reactive_trigger`, `self_heal`

**Governance:** No UPDATE or DELETE endpoints. Append-only by design.

#### `pf_provider_configs` — Multi-Provider Routing

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Config ID |
| `provider_key` | String(50) | NOT NULL, UNIQUE | e.g. anthropic, openai, xai |
| `display_name` | String(100) | NOT NULL | Human-readable name |
| `api_base_url` | String(500) | nullable | Provider API endpoint |
| `supports_batch` | Boolean | NOT NULL, default false | Batch API support |
| `cost_per_1m_input` | Float | nullable | Cost per 1M input tokens |
| `cost_per_1m_output` | Float | nullable | Cost per 1M output tokens |
| `max_context_window` | Integer | nullable | Max context size |
| `circuit_breaker_status` | String(20) | NOT NULL, CHECK | closed, open, half_open |
| `rate_limit_rpm` | Integer | nullable | Rate limit (requests/min) |
| `config` | JSONB | NOT NULL, default {} | Provider-specific settings |
| `enabled` | Boolean | NOT NULL, default true | Provider active |

#### `pf_geo_probes` — GEO Visibility Probe Results

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Probe ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Target campaign |
| `provider` | String(50) | NOT NULL | chatgpt, claude, gemini, perplexity |
| `template_id` | UUID | FK → pf_geo_probe_templates, SET NULL | Source template |
| `prompt_text` | Text | NOT NULL | Query sent to provider |
| `response_excerpt` | Text | nullable | Truncated response |
| `brand_mentioned` | Boolean | NOT NULL, default false | Was entity found? |
| `citation_found` | Boolean | NOT NULL, default false | Was citation present? |
| `sentiment` | String(20) | nullable, CHECK | positive, neutral, negative |
| `competitor_mentions` | JSONB | NOT NULL, default [] | Competitor presence |
| `latency_ms` | Integer | nullable | Response latency |
| `probed_at` | DateTime | NOT NULL | When probe was executed |

#### `pf_geo_probe_templates` — GEO Probe Templates

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Template ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Owner campaign |
| `prompt_text` | Text | NOT NULL | Probe question template |
| `intent_category` | String(100) | nullable | discovery, comparison, recommendation |
| `funnel_stage` | String(50) | nullable | awareness, consideration, decision |
| `auto_generated` | Boolean | NOT NULL, default false | Was template auto-created |

#### `pf_social_draftsets` — Social Media Draft Sets

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Draftset ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Owner campaign |
| `bundle_hash` | String(71) | nullable | EAE evidence bundle hash |
| `intent` | String(50) | nullable | announce, insight, proof, bts |
| `platforms` | JSONB | NOT NULL, default [] | Target platforms |
| `drafts` | JSONB | NOT NULL, default [] | Per-platform drafts |
| `schema_json_ld` | JSONB | nullable | JSON-LD structured data |
| `coverage_warnings` | JSONB | NOT NULL, default [] | EAE coverage warnings |
| `status` | String(20) | NOT NULL, CHECK | draft, reviewed, approved |

#### `pf_prompt_packs` — AI Image Prompt Packs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Pack ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Owner campaign |
| `pack_name` | String(200) | nullable | Display name |
| `sora_prompt` | Text | nullable | Sora (16:9) prompt |
| `chatgpt_image_prompt` | Text | nullable | DALL-E 3 (1:1) prompt |
| `gemini_prompt` | Text | nullable | Imagen 3 (4:3) prompt |
| `negative_constraints` | Text | nullable | What to avoid |
| `aspect_ratios` | JSONB | NOT NULL, default {} | Per-platform sizing |
| `alt_text` | Text | nullable | Accessibility text |
| `status` | String(20) | NOT NULL, CHECK | draft, reviewed, approved |

#### `pf_campaign_outcomes` — Campaign Outcome Signals

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Outcome ID |
| `campaign_id` | UUID | FK → pf_campaigns, CASCADE | Owner campaign |
| `bundle_hash` | String(71) | nullable | Associated EAE bundle |
| `outcome_type` | String(50) | NOT NULL, CHECK | See below |
| `outcome_weight` | Integer | NOT NULL | Signal weight |
| `journalist_id` | UUID | FK → pf_journalists, SET NULL | Associated journalist |
| `notes` | Text | nullable | Free-text notes |
| `context` | JSONB | NOT NULL, default {} | Structured metadata |
| `discovered_at` | DateTime | NOT NULL | When outcome was observed |

**Outcome types (CHECK):** `coverage_secured`, `followup_requested`, `reply_received`, `open_confirmed`, `bounce`, `anti_ai_flagged`

### Column Additions to Existing Tables

#### `pf_campaigns` — New Columns

| Column | Type | Description |
|--------|------|-------------|
| `campaign_type` | String(50) | media, social, geo, mixed |
| `geo_share_pre` | Float | Baseline GEO share before campaign |
| `geo_share_post` | Float | GEO share after automation (updated by geo_share_tracker) |
| `cost_per_cycle` | Float | Average cost per automation cycle |

#### `pf_evidence_items` — New Columns

| Column | Type | Description |
|--------|------|-------------|
| `ai_stance` | String(50) | supportive, neutral, hostile, unknown |
| `disclosure_policy` | Text | Publisher's AI disclosure policy text |

### CRUD Endpoints

All 11 tables follow the standard DataForge CRUD pattern with pagination, filtering, and proper FK cascade handling.

| Table | Endpoints | Notes |
|-------|-----------|-------|
| `pf_automation_jobs` | GET (list), GET/{id}, POST, PATCH/{id} | Job definition management |
| `pf_automation_runs` | GET (list), GET/{id}, POST, PATCH/{id} | Run lifecycle tracking |
| `pf_automation_alerts` | GET (list), GET/{id}, POST, PATCH/{id} | Alert creation + dismiss |
| `pf_automation_overrides` | GET (list), POST | Override creation (TTL-enforced) |
| `pf_agent_logs` | GET (list), GET/{id}, POST | **Append-only — no PATCH/DELETE** |
| `pf_provider_configs` | GET (list), GET/{id}, POST, PATCH/{id} | Provider routing metadata |
| `pf_geo_probes` | GET (list), GET/{id}, POST | Probe result storage |
| `pf_geo_probe_templates` | GET (list), GET/{id}, POST, PATCH/{id}, DELETE/{id} | Template CRUD |
| `pf_social_draftsets` | GET (list), GET/{id}, POST, PATCH/{id} | Draftset lifecycle |
| `pf_prompt_packs` | GET (list), GET/{id}, POST, PATCH/{id} | Prompt pack management |
| `pf_campaign_outcomes` | GET (list), GET/{id}, POST | Outcome signal recording |

### Indexes

| Table | Column(s) | Type | Purpose |
|-------|-----------|------|---------|
| `pf_automation_runs` | `job_id` | btree | FK join performance |
| `pf_automation_runs` | `job_key` | btree | Status queries |
| `pf_automation_alerts` | `run_id` | btree | Run → alerts lookup |
| `pf_automation_alerts` | `job_key` | btree | Job-level alert queries |
| `pf_agent_logs` | `run_id` | btree | Run → log lookup |
| `pf_agent_logs` | `job_key` | btree | Job-level audit queries |
| `pf_automation_overrides` | `job_key` | btree | Override resolution |
| `pf_geo_probes` | `campaign_id` | btree | Campaign probe history |
| `pf_geo_probe_templates` | `campaign_id` | btree | Template lookup |
| `pf_social_draftsets` | `campaign_id` | btree | Campaign draftsets |
| `pf_prompt_packs` | `campaign_id` | btree | Campaign prompt packs |
| `pf_campaign_outcomes` | `campaign_id` | btree | Campaign outcomes |
| `pf_provider_configs` | `provider_key` | unique | Provider lookup |

### Migrations

| Migration | Description |
|-----------|-------------|
| `20260226_0100_pressforge_automation_tables` | Creates 11 new tables with FK relationships |
| `20260226_0200_pressforge_column_additions` | ALTER TABLE additions to `pf_campaigns` and `pf_evidence_items` |

**Dependency:** Both migrations depend on the existing PressForge Phase 2 migration chain (`pressforge_phase2_001` → `pressforge_v12_001` → `pressforge_v12_002`).

### Governance Invariants

1. **`pf_agent_logs` is append-only** — No UPDATE or DELETE at API level
2. **Override TTL enforced** — `expires_at` max 7 days from `created_at`
3. **All automation state in DataForge** — NeuroForge runner is stateless
4. **FK CASCADE on delete** — Deleting a campaign cascades to probes, draftsets, outcomes, templates
5. **FK SET NULL on soft references** — Deleting a run leaves alerts and agent logs intact

### Table Count

After these additions, PressForge uses **21 `pf_*` tables** total:
- Original 10: journalists, campaigns, matches, pitches, outreach_events, coverage, domain_reputation, ai_audit_log, evidence_items, retrieval_runs
- New 11: automation_jobs, automation_runs, automation_alerts, automation_overrides, agent_logs, provider_configs, geo_probes, geo_probe_templates, social_draftsets, prompt_packs, campaign_outcomes

*Added: 2026-02-25*
