# ForgeCommand ↔ VibeForge_BDS Integration Guide

**Version:** 1.0  
**Date:** December 8, 2025  
**Status:** Integration Architecture  

---

## Executive Summary

Wire VibeForge_BDS execution telemetry into ForgeCommand to monitor:
- Skill execution frequency & performance
- PAORT session lifecycle
- SAS compliance enforcement
- Artifact generation rates
- Automation success/failure rates
- Rollback frequency

**New Dashboard:** `/vibeforge-bds` with metrics, charts, and compliance tracking.

---

## 1. Architecture Overview

### Current State

```
ForgeCommand (Dashboard)
├─ Overview Dashboard
├─ NeuroForge Dashboard (LLM costs, tokens)
├─ DataForge Dashboard (search performance)
└─ [Database: dataforge.db]
    ├─ events table (DataForge, NeuroForge, Rake)
    └─ No VibeForge_BDS telemetry yet
```

### After Integration

```
ForgeCommand (Dashboard)
├─ Overview Dashboard (updated with BDS status)
├─ NeuroForge Dashboard
├─ DataForge Dashboard
├─ VibeForge_BDS Dashboard ✨ NEW
│   ├─ Skill Execution Metrics
│   ├─ PAORT Session Tracking
│   ├─ SAS Compliance Monitor
│   ├─ Artifact Generation
│   └─ Performance Charts
└─ [Database: dataforge.db]
    ├─ events table (DataForge, NeuroForge, Rake)
    ├─ vibeforge_bds_executions table ✨ NEW
    ├─ paort_sessions table ✨ NEW
    └─ sas_evaluations table ✨ NEW
```

---

## 2. Database Schema Changes

### Add 3 New Tables to dataforge.db

#### A. vibeforge_bds_executions

```sql
CREATE TABLE vibeforge_bds_executions (
    id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    skill_category TEXT NOT NULL,
    execution_state TEXT NOT NULL,  -- PLAN, ACT, OBSERVE, REFLECT, TERMINAL
    status TEXT NOT NULL,            -- SUCCESS, FAILED, ROLLBACK
    paort_session_id TEXT,
    sas_evaluation_id TEXT,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 2),
    duration_ms INTEGER,
    artifacts_generated INTEGER,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_name ON vibeforge_bds_executions(skill_name);
CREATE INDEX idx_status ON vibeforge_bds_executions(status);
CREATE INDEX idx_created_at ON vibeforge_bds_executions(created_at);
```

#### B. paort_sessions

```sql
CREATE TABLE paort_sessions (
    session_id TEXT PRIMARY KEY,
    vibeforge_bds_execution_id TEXT,
    state TEXT NOT NULL,  -- INIT, CONFIGURED, EXECUTING, APPROVED, COMPLETED, FAILED
    approval_status TEXT,  -- PENDING, APPROVED, REJECTED
    approved_by TEXT,
    approval_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    FOREIGN KEY (vibeforge_bds_execution_id) REFERENCES vibeforge_bds_executions(id)
);

CREATE INDEX idx_session_state ON paort_sessions(state);
CREATE INDEX idx_approval_status ON paort_sessions(approval_status);
```

#### C. sas_evaluations

```sql
CREATE TABLE sas_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    vibeforge_bds_execution_id TEXT,
    skill_name TEXT,
    test_total INTEGER,
    test_passed INTEGER,
    compliance_percentage DECIMAL(5, 2),
    is_compliant BOOLEAN,
    policy_violations TEXT,  -- JSON array of violations
    evaluated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (vibeforge_bds_execution_id) REFERENCES vibeforge_bds_executions(id)
);

CREATE INDEX idx_compliance ON sas_evaluations(compliance_percentage);
CREATE INDEX idx_evaluated_at ON sas_evaluations(evaluated_at);
```

---

## 3. VibeForge_BDS Event Logging

### Integration Point: Log All Skill Executions

When VibeForge_BDS executes a skill, it must log to `dataforge.db`:

```typescript
// In VibeForge_BDS (at skill execution end)

async function logSkillExecution(execution: SkillExecution) {
  const db = await sqlite.open('/path/to/dataforge.db');
  
  // 1. Log execution
  await db.run(
    `INSERT INTO vibeforge_bds_executions 
     (id, skill_name, skill_category, execution_state, status, 
      paort_session_id, sas_evaluation_id, tokens_used, cost_usd, 
      duration_ms, artifacts_generated, started_at, completed_at, error_message)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      execution.id,
      execution.skill.name,
      execution.skill.category,
      execution.finalState,  // TERMINAL after REFLECT
      execution.success ? 'SUCCESS' : 'FAILED',
      execution.paortSessionId,
      execution.sasEvaluationId,
      execution.tokensUsed,
      execution.costUsd,
      execution.durationMs,
      execution.artifactsGenerated.length,
      new Date(execution.startedAt).toISOString(),
      new Date(execution.completedAt).toISOString(),
      execution.errorMessage || null
    ]
  );
  
  // 2. Log PAORT session if exists
  if (execution.paortSession) {
    await db.run(
      `INSERT INTO paort_sessions 
       (session_id, vibeforge_bds_execution_id, state, approval_status, 
        approved_by, approval_reason, retry_count, max_retries, error_message, 
        created_at, completed_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        execution.paortSession.id,
        execution.id,
        execution.paortSession.state,
        execution.paortSession.approvalStatus,
        execution.paortSession.approvedBy || null,
        execution.paortSession.approvalReason || null,
        execution.paortSession.retryCount,
        execution.paortSession.maxRetries,
        execution.paortSession.errorMessage || null,
        new Date(execution.paortSession.createdAt).toISOString(),
        execution.paortSession.completedAt ? new Date(execution.paortSession.completedAt).toISOString() : null
      ]
    );
  }
  
  // 3. Log SAS evaluation if exists
  if (execution.sasEvaluation) {
    await db.run(
      `INSERT INTO sas_evaluations 
       (evaluation_id, vibeforge_bds_execution_id, skill_name, test_total, 
        test_passed, compliance_percentage, is_compliant, policy_violations, evaluated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        execution.sasEvaluation.id,
        execution.id,
        execution.skill.name,
        execution.sasEvaluation.testTotal,
        execution.sasEvaluation.testPassed,
        execution.sasEvaluation.compliancePercentage,
        execution.sasEvaluation.isCompliant,
        JSON.stringify(execution.sasEvaluation.policyViolations),
        new Date(execution.sasEvaluation.evaluatedAt).toISOString()
      ]
    );
  }
  
  await db.close();
}
```

---

## 4. ForgeCommand: Rust IPC Commands

Add these commands to `src-tauri/src/main.rs`:

### A. Skill Execution Metrics

```rust
#[tauri::command]
async fn get_vibeforge_bds_metrics() -> Result<VibeForgeMetrics, String> {
    let db = Connection::open("/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db")
        .map_err(|e| format!("Database error: {}", e))?;
    
    // Total executions (last 24h)
    let total_executions: i32 = db.query_row(
        "SELECT COUNT(*) FROM vibeforge_bds_executions WHERE created_at > datetime('now', '-1 day')",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    // Success rate
    let successful_executions: i32 = db.query_row(
        "SELECT COUNT(*) FROM vibeforge_bds_executions WHERE status = 'SUCCESS' AND created_at > datetime('now', '-1 day')",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    let success_rate = if total_executions > 0 {
        (successful_executions as f64 / total_executions as f64 * 100.0).round() as f32
    } else {
        0.0
    };
    
    // Total artifacts generated
    let total_artifacts: i32 = db.query_row(
        "SELECT COALESCE(SUM(artifacts_generated), 0) FROM vibeforge_bds_executions WHERE created_at > datetime('now', '-1 day')",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    // Average SAS compliance
    let avg_compliance: f64 = db.query_row(
        "SELECT COALESCE(AVG(compliance_percentage), 0) FROM sas_evaluations WHERE evaluated_at > datetime('now', '-1 day')",
        [],
        |row| row.get(0),
    ).unwrap_or(0.0);
    
    // Total PAORT sessions
    let total_paort_sessions: i32 = db.query_row(
        "SELECT COUNT(*) FROM paort_sessions WHERE created_at > datetime('now', '-1 day')",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    // Pending approvals
    let pending_approvals: i32 = db.query_row(
        "SELECT COUNT(*) FROM paort_sessions WHERE approval_status = 'PENDING'",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    Ok(VibeForgeMetrics {
        total_executions,
        successful_executions,
        success_rate,
        total_artifacts,
        avg_sas_compliance: avg_compliance as f32,
        total_paort_sessions,
        pending_approvals,
        rollback_count: db.query_row(
            "SELECT COUNT(*) FROM vibeforge_bds_executions WHERE status = 'ROLLBACK' AND created_at > datetime('now', '-1 day')",
            [],
            |row| row.get(0),
        ).unwrap_or(0),
    })
}

#[derive(serde::Serialize)]
struct VibeForgeMetrics {
    total_executions: i32,
    successful_executions: i32,
    success_rate: f32,
    total_artifacts: i32,
    avg_sas_compliance: f32,
    total_paort_sessions: i32,
    pending_approvals: i32,
    rollback_count: i32,
}
```

### B. Skill Performance Over Time

```rust
#[tauri::command]
async fn get_skill_execution_over_time(hours: i32) -> Result<Vec<ExecutionDataPoint>, String> {
    let db = Connection::open("/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db")
        .map_err(|e| format!("Database error: {}", e))?;
    
    let mut stmt = db.prepare(
        "SELECT 
            strftime('%Y-%m-%d %H:00:00', created_at) as hour,
            COUNT(*) as count,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful
         FROM vibeforge_bds_executions 
         WHERE created_at > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    ).map_err(|e| format!("Query error: {}", e))?;
    
    let datapoints = stmt.query_map([&format!("-{}", hours)], |row| {
        Ok(ExecutionDataPoint {
            timestamp: row.get::<_, String>(0)?,
            total: row.get::<_, i32>(1)?,
            successful: row.get::<_, i32>(2)?,
        })
    }).map_err(|e| format!("Row error: {}", e))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("Collection error: {}", e))?;
    
    Ok(datapoints)
}

#[derive(serde::Serialize)]
struct ExecutionDataPoint {
    timestamp: String,
    total: i32,
    successful: i32,
}
```

### C. SAS Compliance Trend

```rust
#[tauri::command]
async fn get_sas_compliance_over_time(hours: i32) -> Result<Vec<ComplianceDataPoint>, String> {
    let db = Connection::open("/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db")
        .map_err(|e| format!("Database error: {}", e))?;
    
    let mut stmt = db.prepare(
        "SELECT 
            strftime('%Y-%m-%d %H:00:00', evaluated_at) as hour,
            AVG(compliance_percentage) as avg_compliance,
            COUNT(CASE WHEN is_compliant = 1 THEN 1 END) as compliant_count,
            COUNT(*) as total_count
         FROM sas_evaluations 
         WHERE evaluated_at > datetime('now', ? || ' hours')
         GROUP BY hour
         ORDER BY hour ASC"
    ).map_err(|e| format!("Query error: {}", e))?;
    
    let datapoints = stmt.query_map([&format!("-{}", hours)], |row| {
        Ok(ComplianceDataPoint {
            timestamp: row.get::<_, String>(0)?,
            avg_compliance: row.get::<_, f64>(1)?,
            compliant_count: row.get::<_, i32>(2)?,
            total_evaluations: row.get::<_, i32>(3)?,
        })
    }).map_err(|e| format!("Row error: {}", e))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("Collection error: {}", e))?;
    
    Ok(datapoints)
}

#[derive(serde::Serialize)]
struct ComplianceDataPoint {
    timestamp: String,
    avg_compliance: f64,
    compliant_count: i32,
    total_evaluations: i32,
}
```

### D. Top Skills by Execution

```rust
#[tauri::command]
async fn get_top_skills(limit: i32) -> Result<Vec<SkillStats>, String> {
    let db = Connection::open("/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db")
        .map_err(|e| format!("Database error: {}", e))?;
    
    let mut stmt = db.prepare(
        "SELECT 
            skill_name,
            COUNT(*) as executions,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
            AVG(duration_ms) as avg_duration_ms,
            SUM(artifacts_generated) as total_artifacts
         FROM vibeforge_bds_executions 
         WHERE created_at > datetime('now', '-24 hours')
         GROUP BY skill_name
         ORDER BY executions DESC
         LIMIT ?"
    ).map_err(|e| format!("Query error: {}", e))?;
    
    let skills = stmt.query_map([limit], |row| {
        Ok(SkillStats {
            skill_name: row.get::<_, String>(0)?,
            executions: row.get::<_, i32>(1)?,
            successful: row.get::<_, i32>(2)?,
            avg_duration_ms: row.get::<_, i32>(3)?,
            total_artifacts: row.get::<_, i32>(4)?,
        })
    }).map_err(|e| format!("Row error: {}", e))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| format!("Collection error: {}", e))?;
    
    Ok(skills)
}

#[derive(serde::Serialize)]
struct SkillStats {
    skill_name: String,
    executions: i32,
    successful: i32,
    avg_duration_ms: i32,
    total_artifacts: i32,
}
```

### E. PAORT Session Status

```rust
#[tauri::command]
async fn get_paort_session_summary() -> Result<PAORTSummary, String> {
    let db = Connection::open("/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db")
        .map_err(|e| format!("Database error: {}", e))?;
    
    let total_sessions: i32 = db.query_row(
        "SELECT COUNT(*) FROM paort_sessions",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    let completed_sessions: i32 = db.query_row(
        "SELECT COUNT(*) FROM paort_sessions WHERE state = 'COMPLETED'",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    let failed_sessions: i32 = db.query_row(
        "SELECT COUNT(*) FROM paort_sessions WHERE state = 'FAILED'",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    let pending_approvals: i32 = db.query_row(
        "SELECT COUNT(*) FROM paort_sessions WHERE approval_status = 'PENDING'",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    let approved_sessions: i32 = db.query_row(
        "SELECT COUNT(*) FROM paort_sessions WHERE approval_status = 'APPROVED'",
        [],
        |row| row.get(0),
    ).unwrap_or(0);
    
    Ok(PAORTSummary {
        total_sessions,
        completed_sessions,
        failed_sessions,
        pending_approvals,
        approved_sessions,
    })
}

#[derive(serde::Serialize)]
struct PAORTSummary {
    total_sessions: i32,
    completed_sessions: i32,
    failed_sessions: i32,
    pending_approvals: i32,
    approved_sessions: i32,
}
```

### F. Register All Commands

```rust
.invoke_handler(tauri::generate_handler![
    // Existing commands
    get_system_health,
    get_recent_events,
    get_dataforge_metrics,
    get_search_performance_over_time,
    get_neuroforge_metrics,
    get_cost_over_time,
    get_token_usage_over_time,
    
    // NEW: VibeForge_BDS commands
    get_vibeforge_bds_metrics,
    get_skill_execution_over_time,
    get_sas_compliance_over_time,
    get_top_skills,
    get_paort_session_summary,
])
```

---

## 5. ForgeCommand: VibeForge_BDS Dashboard

Create new file: `src/routes/vibeforge-bds/+page.svelte`

```svelte
<script>
  import { onMount } from 'svelte';
  import { invoke } from '@tauri-apps/api/core';
  import LineChart from '$lib/components/LineChart.svelte';

  let metrics = null;
  let topSkills = null;
  let paortSummary = null;
  let executionData = [];
  let complianceData = [];
  let loading = true;
  let error = null;

  async function loadMetrics() {
    try {
      const [m, skills, paort, exec, compliance] = await Promise.all([
        invoke('get_vibeforge_bds_metrics'),
        invoke('get_top_skills', { limit: 10 }),
        invoke('get_paort_session_summary'),
        invoke('get_skill_execution_over_time', { hours: 24 }),
        invoke('get_sas_compliance_over_time', { hours: 24 }),
      ]);
      
      metrics = m;
      topSkills = skills;
      paortSummary = paort;
      executionData = exec;
      complianceData = compliance;
      loading = false;
    } catch (e) {
      error = e.toString();
      loading = false;
    }
  }

  onMount(async () => {
    await loadMetrics();
    const interval = setInterval(loadMetrics, 30000);
    return () => clearInterval(interval);
  });

  const getComplianceColor = (percentage) => {
    if (percentage >= 95) return 'text-green-500';
    if (percentage >= 80) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getStatusColor = (rate) => {
    if (rate >= 95) return 'text-green-500';
    if (rate >= 80) return 'text-yellow-500';
    return 'text-red-500';
  };
</script>

<div class="space-y-6">
  <h1 class="text-4xl font-bold text-white">VibeForge_BDS Dashboard</h1>

  {#if loading}
    <div class="text-center text-gray-400">Loading metrics...</div>
  {:else if error}
    <div class="bg-red-900/20 border border-red-500 p-4 rounded text-red-400">
      Error: {error}
    </div>
  {:else}
    <!-- KPI Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <!-- Total Executions -->
      <div class="bg-gradient-to-br from-violet-900/40 to-violet-900/20 border border-violet-500 p-4 rounded">
        <div class="text-sm text-gray-400">Executions (24h)</div>
        <div class="text-3xl font-bold text-violet-300">{metrics.total_executions}</div>
      </div>

      <!-- Success Rate -->
      <div class="bg-gradient-to-br from-green-900/40 to-green-900/20 border border-green-500 p-4 rounded">
        <div class="text-sm text-gray-400">Success Rate</div>
        <div class={`text-3xl font-bold ${getStatusColor(metrics.success_rate)}`}>
          {metrics.success_rate.toFixed(1)}%
        </div>
      </div>

      <!-- Total Artifacts -->
      <div class="bg-gradient-to-br from-blue-900/40 to-blue-900/20 border border-blue-500 p-4 rounded">
        <div class="text-sm text-gray-400">Artifacts Generated</div>
        <div class="text-3xl font-bold text-blue-300">{metrics.total_artifacts}</div>
      </div>

      <!-- SAS Compliance -->
      <div class="bg-gradient-to-br from-cyan-900/40 to-cyan-900/20 border border-cyan-500 p-4 rounded">
        <div class="text-sm text-gray-400">Avg SAS Compliance</div>
        <div class={`text-3xl font-bold ${getComplianceColor(metrics.avg_sas_compliance)}`}>
          {metrics.avg_sas_compliance.toFixed(1)}%
        </div>
      </div>
    </div>

    <!-- PAORT & Rollback Cards -->
    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <!-- PAORT Sessions -->
      <div class="bg-slate-800/50 border border-slate-700 p-4 rounded">
        <div class="text-sm text-gray-400">PAORT Sessions (24h)</div>
        <div class="text-2xl font-bold text-white">{paortSummary.total_sessions}</div>
        <div class="text-xs text-gray-500 mt-2">
          ✓ {paortSummary.approved_sessions} approved | ⏳ {paortSummary.pending_approvals} pending
        </div>
      </div>

      <!-- Rollback Count -->
      <div class="bg-orange-900/20 border border-orange-500 p-4 rounded">
        <div class="text-sm text-gray-400">Rollbacks (24h)</div>
        <div class="text-2xl font-bold text-orange-400">{metrics.rollback_count}</div>
        <div class="text-xs text-orange-300/70 mt-2">Automated rollbacks detected</div>
      </div>

      <!-- Pending Approvals -->
      <div class="bg-yellow-900/20 border border-yellow-500 p-4 rounded">
        <div class="text-sm text-gray-400">Pending Approvals</div>
        <div class="text-2xl font-bold text-yellow-400">{metrics.pending_approvals}</div>
        <div class="text-xs text-yellow-300/70 mt-2">Awaiting human sign-off</div>
      </div>
    </div>

    <!-- Charts Row 1 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Skill Execution Over Time -->
      {#if executionData.length > 0}
        <LineChart
          title="Skill Executions (24h)"
          labels={executionData.map(d => d.timestamp.substring(11, 16))}
          data={executionData.map(d => d.total)}
          color="#A855F7"
          yAxisLabel="Executions"
          xAxisLabel="Time"
        />
      {/if}

      <!-- SAS Compliance Trend -->
      {#if complianceData.length > 0}
        <LineChart
          title="SAS Compliance Trend (24h)"
          labels={complianceData.map(d => d.timestamp.substring(11, 16))}
          data={complianceData.map(d => d.avg_compliance)}
          color="#06B6D4"
          yAxisLabel="Compliance %"
          xAxisLabel="Time"
        />
      {/if}
    </div>

    <!-- Top Skills Table -->
    <div class="bg-slate-800/50 border border-slate-700 rounded p-6">
      <h2 class="text-xl font-bold text-white mb-4">Top Skills (24h)</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-700">
              <th class="text-left text-gray-400 py-2">Skill Name</th>
              <th class="text-center text-gray-400 py-2">Executions</th>
              <th class="text-center text-gray-400 py-2">Success Rate</th>
              <th class="text-center text-gray-400 py-2">Avg Duration</th>
              <th class="text-center text-gray-400 py-2">Artifacts</th>
            </tr>
          </thead>
          <tbody>
            {#each topSkills as skill}
              <tr class="border-b border-slate-700/50 hover:bg-slate-700/30 transition">
                <td class="py-3 text-white font-mono">{skill.skill_name}</td>
                <td class="text-center text-gray-300">{skill.executions}</td>
                <td class="text-center">
                  <span class={skill.successful === skill.executions ? 'text-green-400' : 'text-yellow-400'}>
                    {((skill.successful / skill.executions) * 100).toFixed(0)}%
                  </span>
                </td>
                <td class="text-center text-gray-300">{skill.avg_duration_ms}ms</td>
                <td class="text-center text-gray-300">{skill.total_artifacts}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- PAORT Session Status -->
    <div class="bg-slate-800/50 border border-slate-700 rounded p-6">
      <h2 class="text-xl font-bold text-white mb-4">PAORT Session Status</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <div class="text-sm text-gray-400">Completed</div>
          <div class="text-2xl font-bold text-green-400">{paortSummary.completed_sessions}</div>
        </div>
        <div>
          <div class="text-sm text-gray-400">Approved</div>
          <div class="text-2xl font-bold text-blue-400">{paortSummary.approved_sessions}</div>
        </div>
        <div>
          <div class="text-sm text-gray-400">Pending</div>
          <div class="text-2xl font-bold text-yellow-400">{paortSummary.pending_approvals}</div>
        </div>
        <div>
          <div class="text-sm text-gray-400">Failed</div>
          <div class="text-2xl font-bold text-red-400">{paortSummary.failed_sessions}</div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  :global(body) {
    background: linear-gradient(135deg, #0D0D0F 0%, #1A1A1D 100%);
  }
</style>
```

---

## 6. Update Overview Dashboard

Update `src/routes/+page.svelte` to include VibeForge_BDS status:

```svelte
<!-- Add to service status cards -->

<div class="bg-gradient-to-br from-violet-900/40 to-violet-900/20 border border-violet-500 p-6 rounded-lg">
  <div class="flex justify-between items-start">
    <div>
      <h3 class="text-lg font-semibold text-white">VibeForge_BDS</h3>
      <div class="mt-2 text-sm text-gray-300">
        <div>Executions (24h): <span class="text-violet-300 font-semibold">{bdsMetrics?.total_executions}</span></div>
        <div>Success Rate: <span class={getStatusColor(bdsMetrics?.success_rate)}>{bdsMetrics?.success_rate.toFixed(1)}%</span></div>
        <div>SAS Compliance: <span class={getComplianceColor(bdsMetrics?.avg_sas_compliance)}>{bdsMetrics?.avg_sas_compliance.toFixed(1)}%</span></div>
      </div>
    </div>
    <div class="text-3xl">⚙️</div>
  </div>
</div>
```

---

## 7. Update Navigation

Update `src/routes/+layout.svelte` to add VibeForge_BDS nav link:

```svelte
<nav class="flex gap-4">
  <a href="/" class:active={$page.route.id === '/'}>Overview</a>
  <a href="/neuroforge" class:active={$page.route.id === '/neuroforge'}>NeuroForge</a>
  <a href="/dataforge" class:active={$page.route.id === '/dataforge'}>DataForge</a>
  <a href="/vibeforge-bds" class:active={$page.route.id === '/vibeforge-bds'}>VibeForge_BDS</a>
</nav>
```

---

## 8. Migration Script

Run this SQL to set up new tables in existing dataforge.db:

```bash
# Run migration
sqlite3 /home/charles/projects/Coding2025/Forge/DataForge/dataforge.db < migration_vibeforge_bds.sql
```

**File: `migration_vibeforge_bds.sql`**

```sql
-- Create VibeForge_BDS tables

CREATE TABLE IF NOT EXISTS vibeforge_bds_executions (
    id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    skill_category TEXT NOT NULL,
    execution_state TEXT NOT NULL,
    status TEXT NOT NULL,
    paort_session_id TEXT,
    sas_evaluation_id TEXT,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 2),
    duration_ms INTEGER,
    artifacts_generated INTEGER,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vf_skill_name ON vibeforge_bds_executions(skill_name);
CREATE INDEX IF NOT EXISTS idx_vf_status ON vibeforge_bds_executions(status);
CREATE INDEX IF NOT EXISTS idx_vf_created_at ON vibeforge_bds_executions(created_at);

CREATE TABLE IF NOT EXISTS paort_sessions (
    session_id TEXT PRIMARY KEY,
    vibeforge_bds_execution_id TEXT,
    state TEXT NOT NULL,
    approval_status TEXT,
    approved_by TEXT,
    approval_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    FOREIGN KEY (vibeforge_bds_execution_id) REFERENCES vibeforge_bds_executions(id)
);

CREATE INDEX IF NOT EXISTS idx_paort_state ON paort_sessions(state);
CREATE INDEX IF NOT EXISTS idx_paort_approval ON paort_sessions(approval_status);

CREATE TABLE IF NOT EXISTS sas_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    vibeforge_bds_execution_id TEXT,
    skill_name TEXT,
    test_total INTEGER,
    test_passed INTEGER,
    compliance_percentage DECIMAL(5, 2),
    is_compliant BOOLEAN,
    policy_violations TEXT,
    evaluated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (vibeforge_bds_execution_id) REFERENCES vibeforge_bds_executions(id)
);

CREATE INDEX IF NOT EXISTS idx_sas_compliance ON sas_evaluations(compliance_percentage);
CREATE INDEX IF NOT EXISTS idx_sas_evaluated_at ON sas_evaluations(evaluated_at);

-- Verify
SELECT 'Tables created successfully' as status;
```

---

## 9. Implementation Checklist

### Phase 1: Database & Backend

- [ ] Add 3 new tables to dataforge.db (vibeforge_bds_executions, paort_sessions, sas_evaluations)
- [ ] Add database migration script
- [ ] Implement 5 new Rust IPC commands
- [ ] Register commands in Tauri handler
- [ ] Test each command with sample queries

### Phase 2: Frontend

- [ ] Create VibeForge_BDS dashboard page
- [ ] Create KPI cards (executions, success, artifacts, compliance)
- [ ] Create PAORT & rollback cards
- [ ] Implement skill execution chart
- [ ] Implement SAS compliance trend chart
- [ ] Create top skills table
- [ ] Create PAORT session status section
- [ ] Add navigation link

### Phase 3: Integration

- [ ] Update Overview dashboard with BDS status
- [ ] Add BDS status to overall system health
- [ ] Test auto-refresh (30-second intervals)
- [ ] Cross-platform testing (Linux, macOS, Windows)

### Phase 4: VibeForge_BDS Changes

- [ ] Add logging to skill execution endpoint
- [ ] Log to dataforge.db on execution completion
- [ ] Log PAORT session state changes
- [ ] Log SAS evaluation results
- [ ] Test logging with real skill executions

---

## 10. Data Flow Diagram

```
VibeForge_BDS
(Executes Skills)
        │
        ├─ Log execution
        ├─ Log PAORT session
        └─ Log SAS evaluation
              │
              ▼
        dataforge.db
        (3 new tables)
              │
              ▼
        ForgeCommand
        (Rust IPC)
              │
              ├─ get_vibeforge_bds_metrics()
              ├─ get_skill_execution_over_time()
              ├─ get_sas_compliance_over_time()
              ├─ get_top_skills()
              └─ get_paort_session_summary()
              │
              ▼
        VibeForge_BDS Dashboard
        (/vibeforge-bds)
              │
              ├─ KPI Cards (executions, success, artifacts, compliance)
              ├─ Charts (execution trend, compliance trend)
              ├─ Top Skills Table
              └─ PAORT Session Status
```

---

## 11. Metrics & KPIs

### Core Metrics

| Metric | Source | Purpose |
|--------|--------|---------|
| **Executions (24h)** | vibeforge_bds_executions | Activity volume |
| **Success Rate** | vibeforge_bds_executions (status) | Reliability |
| **Artifacts Generated** | vibeforge_bds_executions | Productivity |
| **Avg SAS Compliance** | sas_evaluations | Quality gate |
| **PAORT Sessions** | paort_sessions | Approval tracking |
| **Pending Approvals** | paort_sessions (approval_status) | Bottleneck detection |
| **Rollbacks (24h)** | vibeforge_bds_executions (status=ROLLBACK) | Failure recovery |
| **Top Skills** | vibeforge_bds_executions (skill_name) | Usage patterns |

---

## 12. Success Criteria

✅ **Phase 1 Complete When:**
- [ ] All 3 database tables created and indexed
- [ ] All 5 Rust IPC commands implemented and tested
- [ ] VibeForge_BDS dashboard renders without errors
- [ ] All charts populate with sample data
- [ ] Auto-refresh works (30-second intervals)
- [ ] Navigation updated with BDS link

✅ **Phase 2 Complete When:**
- [ ] VibeForge_BDS logs all executions correctly
- [ ] Database records match execution data
- [ ] Charts show real VibeForge_BDS metrics
- [ ] Success rates > 90%
- [ ] SAS compliance tracking accurate

---

## Summary

**Integration bridges VibeForge_BDS with ForgeCommand:**

```
Before:  ForgeCommand monitors DataForge + NeuroForge only
After:   ForgeCommand monitors DataForge + NeuroForge + VibeForge_BDS

New:
├─ 3 database tables (executions, PAORT, SAS)
├─ 5 Rust commands (metrics, trends, skills, PAORT)
├─ 1 new dashboard (/vibeforge-bds)
├─ 2 new charts (execution trends, compliance trends)
├─ 3 new tables (top skills, PAORT status, KPI cards)
└─ Real-time VibeForge_BDS monitoring
```

**Effort: ~40 hours** (database, backend, frontend, testing)

---

**Ready to integrate?** 🚀
