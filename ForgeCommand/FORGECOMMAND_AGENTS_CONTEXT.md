# ForgeCommand Agents Refactoring Context

**Project:** Forge Ecosystem  
**Component:** ForgeCommand (Tauri Desktop App)  
**Goal:** Integrate 5 autonomous monitoring agents into ForgeCommand  
**Timeline:** Jan 2-20, 2026 (Post-VibeForge launch)  
**Owner:** Charles Boswell, Boswell Digital Solutions LLC  

---

## CURRENT FORGECOMMAND STATE (Phase 1)

### Architecture
- **Framework:** Tauri v2 (native desktop app)
- **Frontend:** SvelteKit + TailwindCSS
- **Charting:** Chart.js (4 interactive visualizations)
- **Backend:** Rust IPC commands
- **Database:** SQLite telemetry (dataforge.db)
- **Status:** Production-ready (Phase 1 Complete)

### Existing Dashboards (3)
1. **Overview Dashboard** - System health, service status, uptime, recent events
2. **NeuroForge Dashboard** - LLM costs, token usage, model breakdown, trends
3. **DataForge Dashboard** - Search performance, query metrics, response times

### Existing IPC Commands (7)
- `get_system_health()` → Service status
- `get_recent_events(limit)` → Event feed
- `get_dataforge_metrics()` → Search stats
- `get_search_performance_over_time(hours)` → Time-series
- `get_neuroforge_metrics()` → LLM stats
- `get_cost_over_time(hours)` → Cost time-series
- `get_token_usage_over_time(hours)` → Token time-series

### Current Limitations
- 30-second polling only (no real-time)
- No anomaly detection
- No auto-remediation
- No scheduled reports
- No trend analysis
- No agent integration

---

## 5 AGENTS TO IMPLEMENT

### 1. MONITORING AGENT
**Purpose:** Continuous threshold monitoring and anomaly detection  
**Trigger:** Every 60 seconds (background loop)  
**Runs:** On Render (ForgeAgents service)

**Checks:**
- NeuroForge error rate > 5%
- DataForge search latency > 1000ms
- Rake ingest failure rate > 2%
- ForgeAgents policy violations > 10/hour
- Token cost spike > 3x rolling average

**Output:**
- Write alerts to `events` table
- Severity: warning, critical
- Trigger Diagnostics Agent if critical

**IPC Command Needed:**
```
get_monitoring_agent_status() → { last_run, alerts, next_check }
```

---

### 2. DIAGNOSTICS AGENT
**Purpose:** Deep system analysis when anomalies detected  
**Trigger:** On-demand (button click) or auto-triggered by Monitoring Agent  
**Runs:** On Render (ForgeAgents service)

**Process:**
1. Run health check on all 4 services
2. Query error logs for root cause
3. Test API latency/responsiveness
4. Check resource usage (CPU, memory, DB)
5. Compare metrics to baseline
6. Generate detailed diagnostic report

**Output:**
- Detailed JSON report
- Save to events table
- Display in ForgeCommand modal
- Actionable recommendations

**IPC Command Needed:**
```
trigger_diagnostics_agent() → { report: JSON, status: string }
get_diagnostics_report(report_id) → { full_report: JSON }
```

---

### 3. REMEDIATION AGENT
**Purpose:** Auto-fix common issues  
**Trigger:** Policy-based (when thresholds exceeded)  
**Runs:** On Render (ForgeAgents service)

**Remediation Rules:**
```
1. DataForge DB connection pool exhausted
   → Restart DataForge service
   
2. Rake queue > 1000 jobs
   → Scale up Rake workers
   
3. NeuroForge rate limited by OpenAI
   → Rotate to Claude backend
   → Log action to events table
   
4. Memory usage > 85%
   → Clear vector cache
   → Restart service if > 95%
   
5. API key rotation needed
   → Alert (don't auto-rotate secrets)
```

**Output:**
- Log action taken
- Write to events table
- Notify ForceCommand UI
- Preserve action history

**IPC Command Needed:**
```
get_remediation_history(hours) → { actions: Array }
trigger_manual_remediation(action) → { success: bool, message: string }
```

---

### 4. ANALYTICS AGENT
**Purpose:** Daily trend analysis and cost projections  
**Trigger:** Daily (8 AM)  
**Runs:** On Render (ForgeAgents service)

**Analysis:**
- Calculate token burn rate (tokens/hour)
- Project monthly cost based on usage
- Identify cost drivers (which models, operations)
- Detect trending inefficiencies
- Compare week-over-week metrics
- Suggest optimizations (model switching, rate limiting, etc.)

**Output:**
- JSON insights document
- Save to events table
- Email to Charles (daily summary)
- Display in ForgeCommand (daily insights panel)

**IPC Command Needed:**
```
get_daily_insights() → { insights: JSON, generated_at: timestamp }
get_cost_projection(days_ahead) → { projected_cost: float, confidence: float }
```

---

### 5. REPORT AGENT
**Purpose:** Scheduled weekly reports (PDF)  
**Trigger:** Weekly (Sunday 6 PM)  
**Runs:** On Render (ForgeAgents service)

**Reports Generated:**
1. **Ops Report**
   - System uptime %
   - Error summary
   - Cost breakdown
   - Performance trends
   - Incidents & resolutions

2. **Cost Report**
   - Total spend
   - By-service breakdown
   - Cost per user (estimated)
   - Month/year projections

3. **Health Report**
   - Service status
   - Performance metrics
   - Scaling recommendations
   - Security/policy violations

**Output:**
- Generate PDF files
- Store in ForgeCommand local storage
- Email to Charles
- Archive in events table

**IPC Command Needed:**
```
get_latest_reports() → { reports: Array[{name, date, path}] }
generate_report_now(type) → { report_path: string }
```

---

## DATA FLOW ARCHITECTURE

```
ForgeCommand (Tauri)
    │
    ├─ Dashboard displays status
    ├─ Buttons trigger agent actions
    └─ Polls agent status every 30-60s
         │
         └─ IPC calls to Tauri backend
              │
              └─ HTTP requests to Render
                   │
                   ├─ ForgeAgents Service (Port 8003)
                   │  ├─ Monitoring Agent (runs continuous)
                   │  ├─ Diagnostics Agent (on-demand)
                   │  ├─ Remediation Agent (policy-triggered)
                   │  ├─ Analytics Agent (daily)
                   │  └─ Report Agent (weekly)
                   │
                   ├─ DataForge (Port 8001)
                   │  └─ events table (all logging)
                   │
                   ├─ NeuroForge (Port 8000)
                   │  └─ Metrics querying
                   │
                   └─ Rake (Port 8002)
                      └─ Metrics querying
```

---

## IMPLEMENTATION PHASES

### Phase 1: Monitoring Agent (Jan 2-5)
- ✅ Define thresholds
- ✅ Implement detection logic
- ✅ Write to events table
- ✅ Test locally
- ✅ Deploy to Render

### Phase 2: Diagnostics Agent (Jan 6-10)
- ✅ Build diagnostic checks
- ✅ Report generation
- ✅ ForgeCommand modal integration
- ✅ Test with real scenarios
- ✅ Deploy to Render

### Phase 3: Remediation Agent (Jan 11-15)
- ✅ Define remediation rules
- ✅ Implement auto-fixes
- ✅ Policy engine integration
- ✅ Safety checks (no auto-rotate secrets)
- ✅ Deploy to Render

### Phase 4: Analytics & Report Agents (Jan 16-20)
- ✅ Build analysis logic
- ✅ PDF generation
- ✅ Email integration
- ✅ Test reports
- ✅ Deploy to Render

### Phase 5: ForgeCommand UI (Jan 10+, parallel)
- ✅ Add Rake dashboard
- ✅ Add ForgeAgents dashboard
- ✅ Agent status panel
- ✅ Alerts display
- ✅ Reports viewer
- ✅ Manual trigger buttons

---

## FORGECOMMAND UI ADDITIONS

### New Pages/Sections

**1. Agent Status Panel** (Sidebar or Modal)
```
Status Overview:
├─ Monitoring Agent: Running (last check: 2m ago)
├─ Diagnostics Agent: Ready (last run: 45m ago)
├─ Remediation Agent: Ready (last action: 3h ago)
├─ Analytics Agent: Ready (last run: 24h ago)
└─ Report Agent: Ready (last run: 7d ago)

Action Buttons:
├─ [Run Diagnostics Now]
├─ [View Latest Alerts]
├─ [View Daily Insights]
└─ [Download Latest Report]
```

**2. Alerts Dashboard** (New Page)
```
Real-time Alerts Feed:
├─ 15m ago - ERROR: NeuroForge error rate > 5% [CRITICAL]
├─ 20m ago - WARN: DataForge latency > 1000ms [WARNING]
├─ 42m ago - INFO: Analytics Agent ran daily analysis [INFO]
└─ Older alerts (with archive/dismiss)

Alert Actions:
├─ [View Diagnostics Report]
├─ [Trigger Remediation]
└─ [Acknowledge/Dismiss]
```

**3. Daily Insights Panel** (New Section on Dashboard)
```
Today's Analysis:
├─ Token burn rate: 125k tokens/hour
├─ Projected monthly cost: $8,450 (↑2% vs last week)
├─ Cost drivers:
│  ├─ Claude 3.5 Sonnet: 65% of cost
│  ├─ VibeForge API calls: 40% of volume
│  └─ Suggested optimization: Rate limit to N tokens/hour
└─ Efficiency: ↓5% vs baseline (investigate)

[View Full Analysis] [Subscribe to Daily Email]
```

**4. Reports Viewer** (New Page)
```
Weekly Reports Archive:
├─ [Latest] Ops Report - Dec 10, 2025
│  └─ Download [PDF] | View | Email
├─ Cost Report - Dec 10, 2025
│  └─ Download [PDF] | View | Email
├─ Health Report - Dec 10, 2025
│  └─ Download [PDF] | View | Email
└─ Previous weeks (archive)

[Generate Report Now]
```

**5. Rake Dashboard** (New Page - existing structure)
```
Metrics:
├─ Jobs Queued: 47
├─ Jobs Running: 3
├─ Jobs Completed (24h): 156
├─ Success Rate: 98.4%
├─ Avg Ingest Time: 2.3s
└─ Data Sources: 248 total

Charts:
├─ Ingest Rate Over Time
├─ Success Rate Trend
└─ Queue Depth Over Time
```

**6. ForgeAgents Dashboard** (New Page - existing structure)
```
Metrics:
├─ Active Agents: 3 (Writer, Coder, Analyst)
├─ Tools Executed (24h): 156
├─ Policy Violations: 3
├─ Success Rate: 96.8%
├─ Avg Execution: 4.2s
└─ Memory Usage: 245MB

Charts:
├─ Agent Activity Over Time
├─ Tool Usage Breakdown
└─ Policy Evaluation Trends
```

---

## KEY DATA STRUCTURES

### Alert Event
```json
{
  "service": "neuroforge",
  "event_type": "alert",
  "severity": "critical|warning|info",
  "message": "Error rate exceeded threshold",
  "metrics": {
    "actual_value": 0.08,
    "threshold": 0.05,
    "unit": "percentage"
  },
  "triggered_by": "monitoring_agent",
  "timestamp": "2025-01-10T14:30:00Z",
  "actions_taken": ["trigger_diagnostics"]
}
```

### Diagnostic Report
```json
{
  "report_id": "diag_20250110_143000",
  "triggered_by": "alert|manual",
  "timestamp": "2025-01-10T14:30:00Z",
  "services_checked": {
    "dataforge": { "status": "healthy", "latency_ms": 145 },
    "neuroforge": { "status": "degraded", "error_rate": 0.08 },
    "rake": { "status": "healthy", "queue": 47 },
    "forgeagents": { "status": "healthy", "active": 3 }
  },
  "root_cause_analysis": {
    "service": "neuroforge",
    "probable_causes": ["rate_limited_openai", "model_overload"],
    "evidence": ["8 failures in last 10 requests", "typical of rate limiting"]
  },
  "recommendations": [
    "Switch to Claude backend temporarily",
    "Reduce batch size for requests",
    "Wait 15 minutes before retry"
  ]
}
```

### Daily Insights
```json
{
  "generated_at": "2025-01-10T08:00:00Z",
  "metrics": {
    "token_burn_rate": { "value": 125000, "unit": "tokens/hour" },
    "cost_burn_rate": { "value": 8.50, "unit": "USD/hour" },
    "cost_projection_30d": { "value": 8450, "unit": "USD" },
    "cost_change_vs_last_week": { "value": 2.0, "unit": "percentage", "direction": "up" }
  },
  "cost_drivers": [
    { "category": "model", "name": "claude-3-5-sonnet", "percentage": 65 },
    { "category": "operation", "name": "vibeforge_api_calls", "percentage": 40 }
  ],
  "efficiency": {
    "status": "declining",
    "change_vs_baseline": -5,
    "investigation_needed": true
  },
  "recommendations": [
    "Rate limit VibeForge to 100k tokens/hour",
    "Switch low-priority tasks to cheaper model",
    "Investigate why efficiency declined"
  ]
}
```

---

## INTEGRATION CHECKLIST

### Backend (ForgeAgents on Render)
- [ ] 5 agent implementations in ForgeAgents codebase
- [ ] Event logging to DataForge
- [ ] Error handling & retry logic
- [ ] Health check endpoints
- [ ] Scheduled job system (for daily/weekly agents)
- [ ] Policy engine for Remediation Agent
- [ ] Tool adapters (service restart, scaling, cache management)

### Frontend (ForgeCommand SvelteKit)
- [ ] Agent status panel component
- [ ] Alerts dashboard page
- [ ] Daily insights display
- [ ] Reports viewer page
- [ ] Rake dashboard (new)
- [ ] ForgeAgents dashboard (new)
- [ ] Manual trigger buttons
- [ ] Real-time alert notifications

### IPC Commands (Rust backend)
- [ ] get_monitoring_agent_status()
- [ ] trigger_diagnostics_agent()
- [ ] get_diagnostics_report(report_id)
- [ ] get_remediation_history(hours)
- [ ] trigger_manual_remediation(action)
- [ ] get_daily_insights()
- [ ] get_cost_projection(days_ahead)
- [ ] get_latest_reports()
- [ ] generate_report_now(type)

### Deployment
- [ ] Deploy updated ForgeAgents to Render
- [ ] Update environment variables (agent configs)
- [ ] Test all agents in production
- [ ] Monitor logs for issues
- [ ] Setup email integration for reports
- [ ] Configure alert thresholds

---

## THRESHOLDS & CONFIGURATION

**Monitoring Agent Thresholds:**
```
NeuroForge:
  error_rate_critical: 5%
  error_rate_warning: 2%
  
DataForge:
  latency_critical: 1000ms
  latency_warning: 500ms
  
Rake:
  failure_rate_critical: 5%
  failure_rate_warning: 2%
  
ForgeAgents:
  policy_violations_warning: 10/hour
  policy_violations_critical: 20/hour

Cost:
  spike_threshold: 3x rolling average
```

**Remediation Safety Limits:**
```
Auto-restart allowed for:
  ├─ DataForge
  ├─ Rake
  └─ ForgeAgents (with cooldown)

NOT auto-touched:
  ├─ API keys (only notify)
  ├─ Database (only restart, not modify)
  └─ NeuroForge routing (needs manual decision)

Rate limiting:
  ├─ Max 1 restart per service per 10 minutes
  ├─ Max 2 restarts per service per hour
  └─ Alert if pattern emerges
```

---

## SUCCESS CRITERIA

### Phase Completion
- ✅ All 5 agents deployed and running
- ✅ ForgeCommand UI displays alerts in real-time
- ✅ Daily insights email arrives at 8 AM
- ✅ Weekly reports generated and archived
- ✅ Manual diagnostics working on-demand
- ✅ Auto-remediation tested and safe
- ✅ Zero false positives in first week

### Production Readiness
- ✅ Agents handle network failures gracefully
- ✅ All events logged and queryable
- ✅ Performance impact < 5% on backend services
- ✅ Memory usage stable over 24 hours
- ✅ All IPC commands tested
- ✅ Email delivery reliable
- ✅ PDF generation works

---

## KNOWN CONSTRAINTS

1. **VibeForge ships Jan 1** → Agents are Phase 2 (Jan 2+)
2. **Render deployment required** → Agents must run on backend, not local
3. **Email integration needed** → Setup SendGrid or similar for daily/weekly reports
4. **No WebSocket yet** → Use polling for now (30-60 second intervals)
5. **Secrets management** → API keys read-only (remediation agent never rotates)
6. **Single point of failure** → If Render down, agents don't run (acceptable for MVP)

---

## REFERENCES

**Existing Documentation:**
- ForgeCommand README: `Forge/ForgeCommand/README.md`
- ForgeAgents README: `Forge/ForgeAgents/README.md`
- DataForge README: `Forge/DataForge/README.md`
- NeuroForge README: `Forge/NeuroForge/README.md`

**Related Files:**
- Events table schema: `Forge/DataForge/schema.sql`
- IPC commands: `Forge/ForgeCommand/src-tauri/src/main.rs`
- SvelteKit routes: `Forge/ForgeCommand/src/routes/`

---

## NOTES FOR CHARLES

- **Execution mode:** Build agents incrementally, deploy weekly
- **Real data:** Start with loose thresholds, tighten based on actual metrics
- **Monitoring:** Watch ForgeCommand logs for agent issues first week
- **Iteration:** Weekly agent improvements based on user feedback (even if just you)
- **Timeline:** 3 weeks (Jan 2-20) to full operational agents
- **MVP:** Even with just Monitoring Agent, you have 80% value

---

**Last Updated:** Dec 10, 2025  
**Status:** Ready for implementation  
**Next Step:** Build Monitoring Agent (Jan 2)
