# ForgeCommand Help & Documentation

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen" />
  <img src="https://img.shields.io/badge/System%20Grade-A%20(100%25)-success" />
  <img src="https://img.shields.io/badge/Last%20Updated-Dec%2011%202025-blue" />
</p>

**Welcome to ForgeCommand!** This help page provides quick access to all documentation and guides for getting started with ForgeCommand and the Forge Ecosystem.

---

## 📖 Table of Contents

1. [Quick Start](#-quick-start)
2. [What is ForgeCommand?](#-what-is-forgecommand)
3. [Getting Help](#-getting-help)
4. [Documentation Index](#-documentation-index)
5. [Common Tasks](#-common-tasks)
6. [Ecosystem Services](#-ecosystem-services)
7. [Troubleshooting](#-troubleshooting)
8. [Support](#-support)

---

## 🚀 Quick Start

### First Time Setup

**1. Install Dependencies**
```bash
cd ForgeCommand
npm install
```

**2. Start ForgeCommand**
```bash
npm run tauri:dev
```

**3. Verify Services**
All 4 Forge services should be running:
- ✅ DataForge (Port 8788)
- ✅ NeuroForge (Port 8000)
- ✅ ForgeAgents (Port 8787)
- ✅ Rake (Port 8002)

**Need to start all services?** See [Ecosystem Quick Start Guide](../QUICK_START_GUIDE.md)

---

## 🎯 What is ForgeCommand?

**ForgeCommand** is your mission-control dashboard for the Forge Ecosystem. It provides:

- 📊 **Real-time monitoring** of all Forge services
- 📈 **Interactive charts** showing performance metrics
- 💰 **Cost tracking** for LLM usage across models
- 🔍 **Search analytics** for DataForge vector searches
- ⚡ **Auto-refresh** every 30 seconds
- 🖥️ **Native desktop app** (Linux, macOS, Windows)

### Key Dashboards

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| **Overview** | `/` | System health, service status, recent events |
| **NeuroForge** | `/neuroforge` | LLM costs, token usage, model breakdown |
| **DataForge** | `/dataforge` | Search performance, query volume, error rates |

---

## 🆘 Getting Help

### Quick Help

**I want to...**
- **Get started** → See [Quick Start](#-quick-start) above
- **Understand the architecture** → See [Architecture Documentation](#architecture-documentation)
- **Start all services** → See [Ecosystem Quick Start](../QUICK_START_GUIDE.md)
- **Fix an error** → See [Troubleshooting](#-troubleshooting)
- **Deploy to production** → See [Next Steps Guide](../NEXT_STEPS.md)
- **Understand the code** → See [Development Documentation](#development-documentation)

### By Role

**I am a...**

**👤 End User (Just want to use it)**
- Start here: [ForgeCommand README](README.md#-quick-start)
- Get all services running: [Ecosystem Quick Start](../QUICK_START_GUIDE.md)
- Common commands: [Quick Reference](../QUICK_REFERENCE.md)

**👨‍💻 Developer (Want to modify/extend it)**
- Architecture overview: [README Architecture Section](README.md#-architecture)
- Development guide: [README Development Section](README.md#-development)
- Chart integration: [Phase 1 Complete Guide](docs/PHASE_1_COMPLETE.md)

**🚀 DevOps (Want to deploy it)**
- Deployment roadmap: [Next Steps Guide](../NEXT_STEPS.md)
- Production checklist: [Next Steps - Production Deployment](../NEXT_STEPS.md#production-deployment)
- Service architecture: [Unified Architecture](../docs/architecture/FORGE_UNIFIED_ARCHITECTURE.md)

---

## 📚 Documentation Index

### ForgeCommand Documentation

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[README.md](README.md)** | Complete overview of ForgeCommand | Start here for comprehensive understanding |
| **[HELP.md](HELP.md)** | This file - Quick help & links | When you need to find documentation quickly |
| **[docs/BUILD_COMPLETE.md](docs/BUILD_COMPLETE.md)** | Build guide and setup | When building from source |
| **[docs/PHASE_1_COMPLETE.md](docs/PHASE_1_COMPLETE.md)** | Chart.js integration details | When adding/modifying charts |
| **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** | Detailed setup instructions | When you need step-by-step setup |
| **[docs/TEST_REPORT.md](docs/TEST_REPORT.md)** | Test results and validation | When verifying the build |

### Ecosystem Documentation

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[Quick Start Guide](../QUICK_START_GUIDE.md)** | Get all services running | First time setup, starting services |
| **[Next Steps & Roadmap](../NEXT_STEPS.md)** | Production deployment guide | Planning production deployment |
| **[Quick Reference](../QUICK_REFERENCE.md)** | Command cheatsheet | Quick lookup of commands/endpoints |
| **[Changelog](../CHANGELOG.md)** | Version history | Understanding what changed |
| **[Ecosystem README](../README.md)** | Complete Forge overview | Understanding the full ecosystem |

### Organized Documentation Hub

**Central Index:** [../docs/README.md](../docs/README.md)

All Forge documentation has been organized into categories:

| Category | Location | Contents |
|----------|----------|----------|
| **Guides** | [../docs/guides/](../docs/guides/) | User guides, tutorials, test results |
| **Sessions** | [../docs/sessions/](../docs/sessions/) | Development session reports |
| **Architecture** | [../docs/architecture/](../docs/architecture/) | System design, contracts |
| **VibeForge** | [../docs/vibeforge/](../docs/vibeforge/) | VibeForge-specific docs |
| **Archived** | [../docs/archived/](../docs/archived/) | Historical documentation |

### Architecture Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Unified Architecture](../docs/architecture/FORGE_UNIFIED_ARCHITECTURE.md)** | Complete system design | Architects, developers |
| **[Execution Contract](../docs/architecture/FORGE_GLOBAL_EXECUTION_CONTRACT.md)** | Service contracts & APIs | Integration developers |
| **[Architecture Cleanup](../docs/architecture/ARCHITECTURE_CLEANUP_COMPLETE.md)** | Architecture consolidation | Context on architecture evolution |

### Latest Updates (December 11, 2025)

| Document | Purpose | Status |
|----------|---------|--------|
| **[Session Report](../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md)** | Bug fixes session | ✅ All services 100% operational |
| **[Test Results](../docs/guides/FINAL_TEST_RESULTS.md)** | Complete test validation | ✅ 100% pass rate |
| **[Fixes Applied](../docs/guides/FIXES_APPLIED_SUMMARY.md)** | All bugs resolved | ✅ 5 critical bugs fixed |

---

## 💼 Common Tasks

### Starting ForgeCommand

```bash
# Development mode (with hot-reload)
cd ForgeCommand
npm run tauri:dev

# Production build
npm run tauri:build
```

### Starting All Forge Services

See the [Ecosystem Quick Start Guide](../QUICK_START_GUIDE.md) for comprehensive instructions.

**Quick commands:**
```bash
# DataForge (Port 8788)
cd DataForge
venv/bin/python -m uvicorn app.main:app --port 8788

# NeuroForge (Port 8000)
cd NeuroForge
DATABASE_URL=sqlite:///./neuroforge_telemetry.db neuroforge_backend/.venv/bin/uvicorn neuroforge_backend.main:app --port 8000

# ForgeAgents (Port 8787)
cd ForgeAgents
venv/bin/python -m uvicorn main:app --port 8787

# Rake (Port 8002)
cd rake
source venv/bin/activate
uvicorn app.main:app --port 8002
```

### Checking Service Health

```bash
# All services health check
curl http://localhost:8788/health  # DataForge
curl http://localhost:8000/health  # NeuroForge
curl http://localhost:8787/health  # ForgeAgents
curl http://localhost:8002/health  # Rake
```

Expected response: `{"status":"healthy",...}`

### Viewing Telemetry Data

ForgeCommand reads telemetry from the DataForge database:
```bash
# Database location
/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db

# View events table
sqlite3 DataForge/dataforge.db "SELECT COUNT(*) FROM events;"
```

### Adding New Charts

See the reusable `LineChart` component in [Phase 1 Complete Guide](docs/PHASE_1_COMPLETE.md):

```svelte
<script>
  import LineChart from '$lib/components/LineChart.svelte';
</script>

<LineChart
  title="My Chart"
  labels={chartData.labels}
  data={chartData.values}
  color="#00A3FF"
  yAxisLabel="Value"
  xAxisLabel="Time"
/>
```

### Adding New IPC Commands

1. **Define in Rust** ([src-tauri/src/main.rs](src-tauri/src/main.rs)):
```rust
#[tauri::command]
async fn my_command() -> Result<MyResponse, String> {
    // Implementation
    Ok(MyResponse { /* data */ })
}
```

2. **Register command** (in `main()` function):
```rust
.invoke_handler(tauri::generate_handler![
    my_command,  // Add here
])
```

3. **Call from frontend:**
```typescript
import { invoke } from '@tauri-apps/api/core';
const result = await invoke<MyResponse>('my_command');
```

---

## 🌐 Ecosystem Services

ForgeCommand monitors **4 operational services** (all services ✅ HEALTHY as of December 11, 2025):

### DataForge (Port 8788)
**Purpose:** Vector search & embeddings
**Status:** ✅ HEALTHY
**Documentation:** [DataForge README](../DataForge/README.md)

**Key endpoints:**
- `GET /health` - Health check
- `POST /search` - Vector search
- `POST /embed` - Generate embeddings

### NeuroForge (Port 8000)
**Purpose:** Multi-model AI routing
**Status:** ✅ HEALTHY (5 models available)
**Documentation:** [NeuroForge README](../NeuroForge/neuroforge_backend/README.md)

**Key endpoints:**
- `GET /health` - Health check
- `POST /infer` - AI inference
- `GET /models` - List available models

**Available models:**
- local_general (champion)
- gpt-4, claude-3-opus, claude-3-sonnet
- llama-3-70b

### ForgeAgents (Port 8787)
**Purpose:** AI agents & skills
**Status:** ✅ HEALTHY (120 skills loaded)
**Documentation:** [ForgeAgents README](../ForgeAgents/README.md)

**Key endpoints:**
- `GET /health` - Health check
- `POST /skills/execute` - Execute skill
- `GET /skills` - List skills

### Rake (Port 8002)
**Purpose:** Data ingestion pipeline
**Status:** ✅ HEALTHY
**Documentation:** [Rake README](../rake/README.md)

**Key endpoints:**
- `GET /health` - Health check
- `POST /jobs` - Create ingestion job
- `GET /jobs/{id}` - Check job status

**System Grade:** A (100% functional) - All services operational after December 11 bug fixes

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error:** `Port 1420 is already in use`

**Solution:**
```bash
# Kill process using the port
lsof -ti:1420 | xargs kill -9

# Or change port in vite.config.ts
```

#### 2. Database Connection Error

**Error:** `Failed to connect to database`

**Solution:**
Verify database path in [src-tauri/src/main.rs:65](src-tauri/src/main.rs#L65):
```rust
let database_url = "/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db";
```

Make sure the path exists and is correct for your system.

#### 3. Charts Show "No Data Available"

**Reason:** No telemetry data in database yet

**Solution:**
Generate telemetry by:
- Running DataForge vector searches
- Making NeuroForge inference requests
- Checking events table: `sqlite3 DataForge/dataforge.db "SELECT COUNT(*) FROM events;"`

#### 4. Rust Compilation Errors

**Error:** Compilation fails

**Solution:**
```bash
# Update Rust
rustup update

# Clean and rebuild
cd src-tauri
cargo clean
cargo build
```

#### 5. Service Not Responding

**Error:** `Service at localhost:8788 not responding`

**Solution:**
1. Check if service is running: `curl http://localhost:8788/health`
2. Start the service if needed (see [Starting All Forge Services](#starting-all-forge-services))
3. Check service logs in `/tmp/{ServiceName}_service.log`

#### 6. Missing Dependencies

**Error:** `Module not found` or similar

**Solution:**
```bash
# Clean reinstall
rm -rf node_modules package-lock.json
npm install

# For Rust dependencies
cd src-tauri
cargo clean
cargo build
```

### Still Having Issues?

1. **Check the detailed troubleshooting guide:** [README Troubleshooting](README.md#-troubleshooting)
2. **Review test results:** [Test Report](docs/TEST_REPORT.md)
3. **Check latest session report:** [Dec 11 Session](../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md)
4. **Contact support:** charlesboswell@boswelldigitalsolutions.com

---

## 📞 Support

### Documentation Resources

- **ForgeCommand Docs:** [docs/](docs/) directory
- **Ecosystem Docs:** [../docs/README.md](../docs/README.md)
- **Main README:** [README.md](README.md)
- **Quick Start:** [../QUICK_START_GUIDE.md](../QUICK_START_GUIDE.md)

### Technical Support

- **Email:** charlesboswell@boswelldigitalsolutions.com
- **Latest Status:** [Session Dec 11 Report](../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md)
- **Bug Reports:** Include logs from `/tmp/{ServiceName}_service.log`

### External Documentation

- **Tauri v2:** https://v2.tauri.app/
- **SvelteKit:** https://svelte.dev/docs/kit
- **Chart.js:** https://www.chartjs.org/docs/
- **SQLite:** https://www.sqlite.org/docs.html

---

## 📊 System Status

**Current Status (December 11, 2025):**

| Metric | Status |
|--------|--------|
| **System Grade** | A (100% functional) |
| **Services Operational** | 4/4 (100%) ✅ |
| **Test Pass Rate** | 100% ✅ |
| **Critical Bugs** | 0 ✅ |
| **Production Ready** | Yes ✅ |

**Recent Updates:**
- December 11: All critical bugs fixed (100% operational)
- December 11: Documentation consolidated and organized
- December 5: ForgeCommand Phase 1 complete (charts operational)

---

## 🎯 Quick Links Summary

### For Getting Started
- [Quick Start](#-quick-start)
- [Ecosystem Quick Start Guide](../QUICK_START_GUIDE.md)
- [ForgeCommand README](README.md)

### For Development
- [Development Guide](README.md#-development)
- [Chart Integration](docs/PHASE_1_COMPLETE.md)
- [Architecture](README.md#-architecture)

### For Production
- [Next Steps & Roadmap](../NEXT_STEPS.md)
- [Unified Architecture](../docs/architecture/FORGE_UNIFIED_ARCHITECTURE.md)
- [Execution Contract](../docs/architecture/FORGE_GLOBAL_EXECUTION_CONTRACT.md)

### For Troubleshooting
- [Common Issues](#common-issues)
- [README Troubleshooting](README.md#-troubleshooting)
- [Latest Session Report](../docs/sessions/SESSION_DEC_11_2025_COMPLETE.md)

---

**Last Updated:** December 11, 2025
**Version:** 1.0 (Phase 1 Complete)
**Status:** ✅ Production Ready (All Services Operational - 100%)
**Maintained by:** Boswell Digital Solutions LLC
