# Runtime-promotion schema repair — proposal

Status: PROPOSED 2026-10-05. Not approved. No production change is authorized.

## Evidence

- The live Data Forge service resolves its database to Supabase project `embvfponjxejbtrkryzs`,
  database `postgres`, with no target overrides. Charlie ran a read-only shell check on Render on 2026-10-05.
  The result is the same database that a read-only catalog query inspected.
- That query found no `runtime_promotion_candidates` and no `runtime_promotion_candidate_decisions`
  table in any schema. `alembic_version` holds one revision, `20260930_01`.
- Render logs show `UndefinedTable` on the candidates routes on 2026-09-30.
- The missing tables are a schema-drift fault. They are not a connection-target mistake.
- Source: a GPT Pro diagnostic. A Claude Code session did not run the database queries.

## Scope

The diagnostic checked two tables. Four other runtime-promotion tables come from nearby migrations:
`runtime_promotion_receipts`, `runtime_promotion_approval_decisions`,
`runtime_promotion_execution_requests`, `runtime_promotion_execution_statuses` and
`runtime_promotion_verification_results`. Nobody has checked them. The candidate routes work only if the
candidates table exists. The execution handoff routes need the rest.

## Steps

1. **Audit (read-only).** Compare every table that the Alembic migrations create against the live
   database. Report each missing or partial table. Do this before any design choice. Output: a list in this file.
2. **Find the cause.** Check why the tables are missing: a manual drop, a restore to an older point, or a
   database that never ran those migrations. Use the Supabase project history. A repair that ignores the cause can repeat the fault.
3. **Decide on recovery.** If the tables held data, recover it first (backup or point-in-time restore).
   Charlie decides. Do not create empty replacements before this decision.
4. **Write one forward repair migration** on top of the current head. Confirm that the head is single.
   - For each missing table, create it only when it does not exist. Use the original columns, constraints,
     foreign keys and indexes from the original migrations, plus any later change.
   - If a table exists and its shape differs from the models, stop with an error. Do not alter it silently.
   - Create tables in dependency order: candidates, then decisions and the tables that point at candidates.
   - Enable row-level security with no policies on each new table. This is the same posture as
     `20260711_01_enable_rls_on_drifted_public_tables.py`.
   - Do not stamp, downgrade, or edit `alembic_version` by hand.
5. **Test** on a database copy, using the isolated test runner. Set `NEUROFORGE_URL=http://127.0.0.1:1`.
   - Drifted head: migrate to head, drop the tables, run the repair. The schema must equal the models.
   - Correct head: the repair changes nothing.
   - Partial state: the repair refuses and says which table.
   - The service-key gate on the candidate routes stays unchanged and tested.
6. **Deploy** only after Charlie approves. Render runs `alembic upgrade head` at build. Take a database snapshot first.
7. **Verify.** Run a read-only catalog query for the tables. Then make an authenticated candidates read with the
   `forgecommand` key from Forge_Command Settings (Forge_Command #485). Close FC-RT-20260930-010 only after both pass.

## Decisions for Charlie

- D1: Does lost data need recovery before any repair?
- D2: Repair only the two candidate tables, or every missing runtime-promotion table that step 1 finds?
- D3: Deploy timing, and who takes the snapshot.

## Do not

- Run a blind downgrade, a manual `alembic_version` edit, or `alembic stamp head`.
- Apply a change to the production database before step 6 is approved.
