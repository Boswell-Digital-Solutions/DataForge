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

## Audit result (2026-10-05)

GPT Pro ran [the audit query](runtime_promotion_schema_audit.sql) read-only on project
`embvfponjxejbtrkryzs`. A Claude Code session did not run it. `alembic_version` holds `20260930_01`.

- **56 of 152 expected tables are absent** from `public`. None has a copy in another schema.
- **All seven runtime-promotion tables are absent:** receipts, candidates, candidate decisions, approval
  decisions, execution requests, execution statuses and verification results. The fault is the whole family.
  It is not two tables.
- **49 other tables are absent.** They come from 13 migrations. Counts by migration:
  `add_authorforge_v2_tables` 18, `20260226_0100_pressforge_automation_tables` 11,
  `20251216_1901_add_neuroforge_tables` 4, `20260223_1200_create_agentic_reasoning_tables` 3,
  `add_collab_tables` 3, `20260225_1400_create_eae_tables` 2,
  `20260404_10_create_proving_slice_cloud_tables` 2, `gallery_update_and_collections` 2, and one each from the
  rake jobs, routing decisions and match results migrations.
- `healing_proposals` is one of the 49. Migration `20260606_03` drops it on purpose. It is not drift.
  The other 48 are not yet judged.

**Reading (inference, not established).** So many absent tables across old and new migrations fit a database that was
created some other way, then stamped at a head revision. Another fit is a restore of a schema-only copy. Step 2
must settle this. The proving-slice cloud tables (`ps_cloud_intake_records`, `ps_cloud_receipts`) are among the
absent ones. Forge Command saw `503 cloud_evidence_unavailable` from those handlers. The two facts may be linked.

## Cause investigation (2026-10-05, open)

GPT Pro ran these read-only checks with the Supabase and Render connectors. A Claude Code session did not run
them. The cause is **not established**. The results are summaries of connector output, not provider attestations.

- **Recovery (D1).** The organization reports the Free plan. Free does not include automatic backups or
  point-in-time recovery under the published plan rules. The connector cannot read the backup inventory. So there
  is no verified usable recovery point. A manual export or an older paid-plan backup may still exist. Nobody has checked.
  Do not read this as permission to replace possibly lost data with empty tables.
- **Logs.** No drop, restore, reset or stamp event appears in the windows searched (2 June, 14 July, 30 September,
  and 4 to 5 October). The windows are not the whole project life. The persisted log table `supabase_log_events`
  holds zero rows. The migration ledger holds one entry, `20260907194836`, which is unrelated.
- **Last known good.** Unknown. The first known bad time is 2026-09-30 10:24:10 UTC (`42P01`, log
  `e6a15ee5-c625-4e64-8757-8163cc41e657`). There are 14 such errors on that day. The tables may have been absent
  long before. Render logs show no candidates request from 6 to 29 September.
- **Surviving rows.** `users` (19) and `projects` (432) hold rows dated from 1 March. `api_keys` (4) holds rows from
  2 June. A restore or import can keep old dates, so this does not prove the missing tables ever existed here.
- **Stamp or proof script on production.** Not established. Render logs from 6 September to 5 October show no
  `stamp` or `prove_` line. A command can run without a log line. The statement statistics were reset on 2026-10-02,
  after the failure, so they cannot show the cause.

**Open check (Charlie):** In the Supabase dashboard for DataForgedb, open Database, then Backups. Read the
Scheduled and Point in Time pages. Record the availability message and any earliest and latest recovery dates.
Do not start a restore.

## Steps

1. **Audit (read-only).** Compare every table that the Alembic migrations create against the live
   database. Report each missing or partial table. Do this before any design choice. Query: [runtime_promotion_schema_audit.sql](runtime_promotion_schema_audit.sql). It is read-only. Output: a list in this file.
2. **Find the cause.** Check why the tables are missing: a manual drop, a restore to an older point, or a
   database that never ran those migrations. A repair that ignores the cause can repeat the fault.
   - *Repo findings (checked 2026-10-05):* The Render build runs `python -m alembic upgrade head` at every deploy
     (`scripts/render-build.sh:33`). At head it changes nothing, so a build cannot restore missing tables.
     Several proof scripts run `alembic stamp 20260714_01` on a scratch fixture database. A database in that
     state shows a head revision without the older tables. No repo file explains the production state.
   - *Supabase and Render checks (open):* (a) Is point-in-time recovery or a backup available, and from which date?
     (b) Do Postgres logs or the audit log show a `DROP TABLE`, a restore or a schema reset, and when?
     (c) When did the candidates route last answer without `UndefinedTable`? Search Render logs before 2026-09-30.
     (d) Do the surviving tables (for example `api_keys`) hold rows older than the missing tables' migrations?
     (e) Did anyone run a proof script or `alembic stamp` against the production URL?
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

- D1: Does lost data need recovery before any repair? No usable recovery point is verified. The Backups screen decides this.
- D2: Repair the seven runtime-promotion tables only, or also the other 48 absent tables? The audit shows the
  runtime-promotion family is wholly absent. The other 48 belong to several systems. Each system owner must
  confirm that its tables are still wanted. A table that nothing uses should not be recreated.
- D3: Deploy timing, and who takes the snapshot.

## Do not

- Run a blind downgrade, a manual `alembic_version` edit, or `alembic stamp head`.
- Apply a change to the production database before step 6 is approved.
