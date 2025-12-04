# Forge Telemetry - Quick Start Guide

🎉 **Telemetry is ready to use!** Here's everything you need to get started.

---

## ✅ What's Already Done

- [x] **Events table** created in DataForge database
- [x] **forge-telemetry** Python package built and tested
- [x] **Installed** in DataForge and NeuroForge
- [x] **Examples** created for both services
- [x] **Tests** passing (5/5)

---

## 🚀 Quick Start (3 Steps)

### 1. Import the telemetry client

```python
from forge_telemetry import TelemetryClient
import uuid
import time

telemetry = TelemetryClient()
```

### 2. Add telemetry to your function

```python
@app.post("/api/endpoint")
async def my_endpoint(data: dict):
    correlation_id = uuid.uuid4()
    start = time.time()

    try:
        result = await do_work(data)

        # Emit success event
        telemetry.emit(
            service="dataforge",  # or "neuroforge", "rake"
            event_type="query",
            correlation_id=correlation_id,
            metadata={"query": data.get("query")},
            metrics={"duration_ms": (time.time() - start) * 1000}
        )

        return result

    except Exception as e:
        # Emit error event
        telemetry.emit(
            service="dataforge",
            event_type="query_error",
            severity="error",
            correlation_id=correlation_id,
            metadata={"error": str(e)}
        )
        raise
```

### 3. Run and verify

```bash
# Test your endpoint
curl -X POST http://localhost:8001/api/endpoint

# Check telemetry was emitted
sqlite3 DataForge/dataforge.db "SELECT * FROM events ORDER BY timestamp DESC LIMIT 5;"
```

---

## 📂 Files & Examples

### Try the Examples

**DataForge example:**
```bash
cd DataForge
source venv/bin/activate
python examples/telemetry_example.py
```

**NeuroForge example:**
```bash
cd NeuroForge
source venv/bin/activate
python examples/telemetry_example.py
```

**Test suite:**
```bash
cd DataForge
source venv/bin/activate
python examples/test_telemetry.py
```

### Key Files

```
Forge/
├── forge-telemetry/              # Shared telemetry package
│   ├── forge_telemetry/
│   │   ├── __init__.py
│   │   ├── client.py           # TelemetryClient
│   │   └── models.py           # Event models
│   └── README.md               # Package docs
│
├── DataForge/
│   ├── examples/
│   │   ├── telemetry_example.py   # Integration examples
│   │   └── test_telemetry.py      # Test suite
│   └── scripts/
│       └── create_events_table.py # Table creation
│
├── NeuroForge/
│   └── examples/
│       └── telemetry_example.py   # NeuroForge examples
│
├── TELEMETRY_SETUP_COMPLETE.md      # Full documentation
├── TELEMETRY_INTEGRATION_GUIDE.md    # Integration patterns
└── TELEMETRY_QUICK_START.md          # This file
```

---

## 🎯 Event Types to Use

### DataForge (Blue)
- `query` - Search completed
- `query_error` - Search failed
- `ingestion` - Documents added
- `ingestion_error` - Ingestion failed

### NeuroForge (Violet)
- `model_request` - LLM call completed
- `model_error` - LLM call failed

### Rake (Cyan) - When you build it
- `job_started` - Pipeline started
- `job_completed` - Pipeline finished
- `job_failed` - Pipeline failed
- `phase_completed` - Stage finished (fetch/clean/chunk/embed/store)

---

## 💡 Key Patterns

### Pattern 1: Basic Event
```python
telemetry.emit(
    service="dataforge",
    event_type="query",
    correlation_id=uuid.uuid4(),
    metadata={"query": "search term"},
    metrics={"duration_ms": 123, "results": 10}
)
```

### Pattern 2: Error Handling
```python
try:
    result = await do_work()
    telemetry.emit(event_type="success", ...)
except Exception as e:
    telemetry.emit(
        event_type="error",
        severity="error",
        metadata={"error": str(e)}
    )
    raise
```

### Pattern 3: Distributed Tracing
```python
# Service A generates correlation_id
correlation_id = uuid.uuid4()

# Service A emits event
telemetry.emit(service="neuroforge", correlation_id=correlation_id, ...)

# Service A calls Service B with correlation_id in header
response = await httpx.post(
    "http://dataforge:8001/api/search",
    headers={"X-Correlation-ID": str(correlation_id)}
)

# Service B uses same correlation_id
correlation_id = request.headers.get("X-Correlation-ID")
telemetry.emit(service="dataforge", correlation_id=correlation_id, ...)

# Now you can trace the entire request chain!
```

---

## 📊 Querying Events

### Latest events
```sql
SELECT * FROM events
ORDER BY timestamp DESC
LIMIT 10;
```

### Events by service
```sql
SELECT service, event_type, COUNT(*) as count
FROM events
GROUP BY service, event_type;
```

### Track a distributed request
```sql
SELECT service, event_type, timestamp, metrics
FROM events
WHERE correlation_id = 'your-correlation-id-here'
ORDER BY timestamp ASC;
```

### Error rate by service
```sql
SELECT
    service,
    COUNT(*) as total,
    SUM(CASE WHEN severity = 'error' THEN 1 ELSE 0 END) as errors,
    ROUND(100.0 * SUM(CASE WHEN severity = 'error' THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_pct
FROM events
GROUP BY service;
```

---

## ⚙️  Configuration

### Shared Database

All services use the **same database** for telemetry:

**DataForge/.env:**
```bash
DATABASE_URL=sqlite:///./dataforge.db
```

**NeuroForge/.env:**
```bash
# Point to DataForge's database for shared telemetry
DATABASE_URL=sqlite:////home/charles/projects/Coding2025/Forge/DataForge/dataforge.db
```

**Rake/.env** (when you build it):
```bash
# Point to DataForge's database for shared telemetry
DATABASE_URL=sqlite:////home/charles/projects/Coding2025/Forge/DataForge/dataforge.db
```

### PostgreSQL (Production)

For production, use PostgreSQL:

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/dataforge
```

The telemetry client automatically detects and supports both SQLite and PostgreSQL.

---

## ✨ Next Steps

### Week 2: Add to Endpoints (In Progress)

**DataForge:**
- [ ] Add to search endpoint ([app/api/search_router.py:42](app/api/search_router.py#L42))
- [ ] Add to ingestion endpoint ([app/api/projects_router.py:67](app/api/projects_router.py#L67))
- [ ] Add to error handlers

**NeuroForge:**
- [ ] Add to prompt endpoint ([neuroforge_backend/main.py:123](neuroforge_backend/main.py#L123))
- [ ] Track token usage and costs
- [ ] Add to model selection logic

**Rake:**
- [ ] Build with telemetry from day one
- [ ] Emit events for each pipeline stage

### Week 3: Forge Command Dashboard

- [ ] Initialize Tauri project
- [ ] Build real-time metrics dashboard
- [ ] Add service-specific dashboards (blue/violet/cyan themes)
- [ ] System tray integration

### Week 4: Polish

- [ ] Native notifications for errors
- [ ] Alerting rules (error rate > 5%)
- [ ] Cost forecasting (NeuroForge)
- [ ] Production deployment

---

## 🐛 Troubleshooting

**Q: Events not showing up?**
```bash
# Check if table exists
sqlite3 DataForge/dataforge.db ".tables"

# If not, create it:
cd DataForge
python scripts/create_events_table.py
```

**Q: "No module named 'forge_telemetry'"?**
```bash
pip install -e /path/to/forge-telemetry
```

**Q: Correlation IDs not linking requests?**
- Make sure you're passing `X-Correlation-ID` header between services
- Use the SAME correlation_id for all related events

**Q: Telemetry is failing but app works?**
- This is expected! Telemetry client catches errors and prints warnings
- Your app continues even if telemetry breaks
- Check the warnings in your logs

---

## 📚 Documentation

- **[TELEMETRY_SETUP_COMPLETE.md](TELEMETRY_SETUP_COMPLETE.md)** - Full implementation details
- **[TELEMETRY_INTEGRATION_GUIDE.md](TELEMETRY_INTEGRATION_GUIDE.md)** - Patterns and best practices
- **[forge-telemetry/README.md](forge-telemetry/README.md)** - Package documentation
- **[FORGE_CONTEXT.md](FORGE_CONTEXT.md)** - Project architecture

---

## 🎯 Success Metrics

**Current Status:**
- ✅ Infrastructure: 100% complete
- ✅ Testing: 5/5 tests passing
- ⏸️  Endpoint Coverage: 0% (to be done this week)

**Goals:**
- 🎯 95%+ endpoint coverage
- 🎯 <2s dashboard load time
- 🎯 <5% false positive alerts
- 🎯 100% correlation_id propagation

---

**Ready to add telemetry to your endpoints? Start with the [Integration Guide](TELEMETRY_INTEGRATION_GUIDE.md)!**

*Generated with [Claude Code](https://claude.com/claude-code)*
