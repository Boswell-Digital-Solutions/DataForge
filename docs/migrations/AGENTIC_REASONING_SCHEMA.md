# Agentic Reasoning — DataForge Schema Plan

**Date:** February 23, 2026
**Status:** Schema plan — Alembic migration to be written in Session 3
**Dependencies:** pgvector extension (already enabled in initial migration `9fe94997bec5`)

---

## Table 1: `execution_experiences`

Stores execution outcome records for the Experience Store. Used for semantic retrieval during the Plan phase.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `experience_id` | UUID | PK | `gen_random_uuid()` default |
| `run_id` | UUID | FK to `forge_runs(run_id)`, NOT NULL | Links to the execution run |
| `agent_id` | UUID | NOT NULL | Agent that produced this experience |
| `agent_archetype` | VARCHAR(50) | NOT NULL | Agent archetype for filtering |
| `task_embedding` | vector(768) | NOT NULL | pgvector 768-dim embedding |
| `target_scope` | JSONB | NOT NULL | Execution target scope |
| `execution_summary` | TEXT | NOT NULL | 2-3 sentence outcome summary |
| `outcome` | VARCHAR(20) | CHECK (outcome IN ('success', 'partial', 'failure')), NOT NULL | Execution result |
| `gate_results_snapshot` | JSONB | nullable | BuildGuard gate results snapshot |
| `tool_sequence` | JSONB | nullable | Ordered list of tool calls |
| `duration_ms` | INTEGER | nullable | Wall-clock time in milliseconds |
| `cost_usd` | NUMERIC(10,4) | nullable | Total LLM API cost |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record creation time |

### Indexes

| Name | Type | Columns | Notes |
|------|------|---------|-------|
| `ix_execution_experiences_embedding` | IVFFlat | `task_embedding` | `lists=100`, cosine distance |
| `ix_execution_experiences_archetype_outcome` | B-tree | `(agent_archetype, outcome)` | Filter by archetype + outcome |
| `ix_execution_experiences_run_id` | B-tree | `run_id` | FK lookup |
| `ix_execution_experiences_created_at` | B-tree | `created_at` | Time-range queries |
| `ix_execution_experiences_target_scope` | GIN | `target_scope` | JSONB query support |
| `ix_execution_experiences_gate_results` | GIN | `gate_results_snapshot` | JSONB query support |

---

## Table 2: `skill_nominations`

Tracks the lifecycle of skill promotion candidates from detection through registration.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `nomination_id` | UUID | PK | `gen_random_uuid()` default |
| `candidate_name` | VARCHAR(200) | NOT NULL | Auto-generated from tool sequence |
| `tool_sequence` | JSONB | NOT NULL | Ordered list of tool names |
| `parameter_schemas` | JSONB | nullable | Parameter schemas from tool calls |
| `evidence_run_ids` | UUID[] | NOT NULL | Array of evidence run IDs |
| `proposed_capability_category` | CHAR(1) | CHECK (proposed_capability_category IN ('A','B','C','D','E','F','G')) | Capability category |
| `proposed_capability_id` | VARCHAR(200) | nullable | Proposed capability identifier |
| `status` | VARCHAR(20) | CHECK (status IN ('candidate', 'nominated', 'reviewing', 'approved', 'registered', 'rejected')), DEFAULT 'candidate' | Lifecycle state |
| `rejection_reason` | TEXT | nullable | Reason if rejected |
| `reviewed_by` | VARCHAR(200) | nullable | Reviewer identity |
| `reviewed_at` | TIMESTAMPTZ | nullable | Review timestamp |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation time |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update time |

### Indexes

| Name | Type | Columns | Notes |
|------|------|---------|-------|
| `ix_skill_nominations_status` | B-tree | `status` | Filter by lifecycle state |
| `ix_skill_nominations_created_at` | B-tree | `created_at` | Time-range queries |

---

## Table 3: `governed_broadcasts`

Records all governed broadcast messages for audit and delivery tracking.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `broadcast_id` | UUID | PK | `gen_random_uuid()` default |
| `source_agent_id` | UUID | NOT NULL | Sending agent ID |
| `source_run_id` | UUID | FK to `forge_runs(run_id)`, NOT NULL | Sending run ID |
| `target_scope` | JSONB | NOT NULL | RunIntent target matching criteria |
| `knowledge_type` | VARCHAR(30) | CHECK (knowledge_type IN ('context_discovery', 'error_signal', 'dependency_finding', 'scope_overlap')), NOT NULL | Broadcast type |
| `payload` | JSONB | NOT NULL | Structured knowledge packet (max 4KB enforced at API) |
| `provenance` | JSONB | nullable | Source ECD reference |
| `trust_metadata` | JSONB | nullable | Source agent trust tier |
| `delivered_to` | UUID[] | DEFAULT '{}' | Agent IDs that received this broadcast |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Send time |

### Indexes

| Name | Type | Columns | Notes |
|------|------|---------|-------|
| `ix_governed_broadcasts_source_run_id` | B-tree | `source_run_id` | FK lookup |
| `ix_governed_broadcasts_knowledge_type` | B-tree | `knowledge_type` | Filter by type |
| `ix_governed_broadcasts_created_at` | B-tree | `created_at` | Time-range queries |
| `ix_governed_broadcasts_target_scope` | GIN | `target_scope` | JSONB query support |
| `ix_governed_broadcasts_payload` | GIN | `payload` | JSONB query support |

---

## Migration Notes

- pgvector extension is already enabled (initial migration `9fe94997bec5_initial_database_schema.py`)
- IVFFlat index on `task_embedding` uses `lists=100` — suitable for initial data volume, may need tuning as experience count grows
- All JSONB columns have GIN indexes for query performance
- `forge_runs` table must exist before creating FK references — verify in migration
- Include `downgrade()` function that drops all three tables in reverse order
- Migration filename: `YYYYMMDD_HHMM_create_agentic_reasoning_tables.py`
