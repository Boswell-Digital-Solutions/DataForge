# Load Testing Guide - DataForge

> The checked-in legacy load scripts still contain `/api/projects` scenarios. That route is now
> a `410 Gone` boundary tombstone; do not treat those scenarios or historical numbers as an
> AuthorForge content API benchmark.

This guide explains how to run comprehensive load tests on the DataForge API using multiple tools.

## Quick Start

### Option 1: Using Pytest + requests (No external tools)

```bash
# Run 50 concurrent users for 30 seconds
pytest tests/load/test_k6_load.py::TestLoadPerformance::test_50_concurrent_users_30_seconds -v

# Run 100 concurrent users for 60 seconds
pytest tests/load/test_k6_load.py::TestLoadPerformance::test_100_concurrent_users_60_seconds -v

# Run all load tests
pytest tests/load/test_k6_load.py -v -m load
```

### Option 2: Using K6 (Recommended for production)

#### Installation

**macOS:**

```bash
brew install k6
```

**Linux (apt):**

```bash
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Docker:**

```bash
docker run -i grafana/k6 run - < tests/load/k6_test.js
```

#### Running K6 Tests

**Basic run (default: 50 users, 1 minute):**

```bash
k6 run tests/load/k6_test.js
```

**Custom parameters:**

```bash
# 100 concurrent users for 5 minutes
k6 run tests/load/k6_test.js --vus 100 --duration 5m

# With custom host
k6 run tests/load/k6_test.js --vus 50 --duration 2m -e BASE_URL=http://api.example.com

# Verbose output
k6 run tests/load/k6_test.js -v
```

**With metrics output:**

```bash
# Generate JSON summary
k6 run tests/load/k6_test.js --out json=results/summary.json

# Real-time metrics (requires Grafana Cloud)
k6 run tests/load/k6_test.js --out cloud
```

## Test Scenarios

### Scenario 1: Baseline Performance (Light Load)

```bash
k6 run tests/load/k6_test.js --vus 10 --duration 60s
```

**Expected:**

- Response time: < 200ms average
- Success rate: > 99%
- No errors

### Scenario 2: Normal Load

```bash
k6 run tests/load/k6_test.js --vus 50 --duration 300s
```

**Expected:**

- Response time: < 500ms average
- Success rate: > 95%
- Minimal errors

### Scenario 3: Stress Test (High Load)

```bash
k6 run tests/load/k6_test.js --vus 100 --duration 600s
```

**Expected:**

- Response time: < 1000ms average
- Success rate: > 90%
- Some errors acceptable

### Scenario 4: Spike Test (Sudden Traffic)

```bash
k6 run tests/load/k6_spike_test.js
```

Ramps up to 100 users in 10 seconds, holds for 30 seconds, then ramps down.

## Pytest Load Testing Usage

The pytest-based load testing suite provides an alternative without external tools:

### Features

- **Pure Python:** No external tool installation required
- **Concurrent Users:** Thread-based concurrency simulation
- **Realistic Workload:** Simulates actual user behavior
- **Detailed Metrics:** Response time distribution, success rates, error tracking
- **Pytest Integration:** Works with existing test infrastructure

### Example: Run 25 Users for 15 Seconds

```bash
pytest tests/load/test_k6_load.py::TestLoadPerformance::test_response_time_benchmarks -v -s
```

### Metrics Output

```
================================================================================
LOAD TEST REPORT
================================================================================

Duration: 15.2s
Concurrent Users: 25

Endpoint                      Requests    Success Rate    Avg (ms)       P95 (ms)
--------------------------------------------------------------------------------
/api/projects (410 tombstone)    125        100.0%         25.0          60.0
/api/search                       89         98.1%        245.7         512.3
/api/diligence                    67         92.1%        512.8         1023.4
--------------------------------------------------------------------------------
TOTAL                           281         95.0%

Throughput: 18.5 requests/second

⚠️  ERRORS DETECTED:
  /api/diligence: 5 failures
    - Connection timeout
```

## Locust Load Testing Usage

The Locust framework provides web-based control and real-time monitoring:

```bash
# Start Locust web UI
locust -f tests/load/locustfile.py --host=http://localhost:8788

# Then open http://localhost:8089 in your browser
```

**Web UI:**

1. Enter number of users (e.g., 50)
2. Enter spawn rate (e.g., 5 users/sec)
3. Click "Start swarming"
4. Monitor real-time metrics and charts

**Command line (headless):**

```bash
locust -f tests/load/locustfile.py \
  --host=http://localhost:8788 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --headless
```

## Performance Benchmarks

### Expected Response Times

| Endpoint            | P50   | P95    | P99    | Max   |
| ------------------- | ----- | ------ | ------ | ----- |
| GET /api/projects (410 tombstone) | 25ms | 75ms | 150ms | 300ms |
| POST /api/projects (410 tombstone) | 25ms | 75ms | 150ms | 300ms |
| GET /api/search     | 300ms | 1000ms | 2000ms | 3s    |
| POST /api/diligence | 400ms | 1000ms | 2000ms | 3s    |
| GET /health         | 50ms  | 100ms  | 150ms  | 300ms |

### Expected Success Rates

| Load Level | Success Rate |
| ---------- | ------------ |
| 10 users   | > 99%        |
| 50 users   | > 95%        |
| 100 users  | > 90%        |
| 200+ users | > 80%        |

## Troubleshooting

### Connection Refused

**Problem:** `Connection refused` errors

**Solution:**

```bash
# Ensure API is running
curl http://localhost:8788/health

# If not running, start it
docker-compose up
```

### Timeout Errors

**Problem:** Request timeouts at high concurrency

**Solution:**

1. Increase connection pool size in API config
2. Optimize database queries
3. Add caching layer
4. Scale horizontally

### Memory Usage Issues

**Problem:** High memory usage during tests

**Solution:**

```bash
# Reduce number of concurrent users
k6 run tests/load/k6_test.js --vus 25

# Or use K6 on separate machine
docker run -i grafana/k6 run - < tests/load/k6_test.js
```

## Integrating with CI/CD

### GitHub Actions Example

```yaml
name: Load Tests

on: [push]

jobs:
  load-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install K6
        run: |
          sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Start API
        run: python -m uvicorn app.main:app --port 8788 &

      - name: Run load tests
        run: k6 run tests/load/k6_test.js --vus 25 --duration 60s
```

## Analyzing Results

### K6 JSON Output

```bash
k6 run tests/load/k6_test.js --out json=results/summary.json
```

View results:

```bash
python -c "
import json
with open('results/summary.json') as f:
    data = json.load(f)
    print(json.dumps(data['metrics'], indent=2))
"
```

### Pytest CSV Export

```bash
pytest tests/load/test_k6_load.py --csv=results/load_test.csv
```

### Comparison Across Runs

```bash
# Save baseline
k6 run tests/load/k6_test.js --out json=results/baseline.json

# Run after changes
k6 run tests/load/k6_test.js --out json=results/current.json

# Compare (requires custom script)
python scripts/compare_load_tests.py results/baseline.json results/current.json
```

## Best Practices

1. **Isolate Tests:** Run load tests on isolated test environment
2. **Warm Up:** Run light load first to warm up caches
3. **Realistic Data:** Use production-like data volume
4. **Monitor Infrastructure:** Track CPU, memory, disk, network during tests
5. **Baseline First:** Establish baseline before optimizations
6. **Incremental Load:** Gradually increase load to identify breaking points
7. **Long Duration:** Run for at least 5-10 minutes for stable results
8. **Multiple Runs:** Run tests multiple times for consistency

## Monitoring During Tests

### Terminal 1: Run API with metrics

```bash
# With prometheus metrics
uvicorn app.main:app --port 8788 &
```

### Terminal 2: Watch system metrics

```bash
# CPU and memory
top

# Or use htop for better interface
htop
```

### Terminal 3: Run load test

```bash
k6 run tests/load/k6_test.js --vus 50 --duration 5m
```

### Terminal 4: Monitor database

```bash
# PostgreSQL connections
psql -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Check every 5 seconds
watch -n 5 "psql -c \"SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;\""
```

## Advanced Scenarios

### Custom Script: Weighted Task Distribution

See `tests/load/locustfile.py` for weighted task implementation:

- 30% GET projects
- 20% POST projects
- 15% Search
- 10% GET single
- 10% PUT projects
- 8% POST diligence
- 5% Add findings
- 2% Health check

### Custom Script: Think Time

Users think 1-3 seconds between operations to simulate realistic behavior.

### Custom Script: Error Handling

Tests handle transient errors and retries automatically.

## Results Interpretation

### Good Results

- Response times: P95 < 1s, P99 < 2s
- Success rate: > 95% at 50+ concurrent users
- Throughput: Consistent across duration
- No memory leaks: Stable memory usage

### Warning Signs

- Increasing response times over time (memory leak)
- Success rate dropping under load (resource exhaustion)
- Spikes in errors at specific times (connection pool issues)
- High CPU/memory usage (inefficient code)

## Next Steps

1. **Baseline:** Establish current performance
2. **Identify Bottlenecks:** Profile under load
3. **Optimize:** Database queries, caching, etc.
4. **Retest:** Validate improvements
5. **Monitor:** Track performance over time

For more information, see:

- K6: https://k6.io/docs/
- Locust: https://locust.io/
- Pytest: https://docs.pytest.org/
