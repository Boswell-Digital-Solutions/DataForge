# DataForge Operations Runbook

**Version:** 5.1  
**Last Updated:** November 21, 2025

This runbook provides step-by-step procedures for daily operations, monitoring, maintenance, and incident response.

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Monitoring & Alerting](#monitoring--alerting)
3. [Maintenance Tasks](#maintenance-tasks)
4. [Incident Response](#incident-response)
5. [Performance Tuning](#performance-tuning)
6. [Backup & Recovery](#backup--recovery)

---

## Daily Operations

### Morning Health Check (8:00 AM Daily)

**Duration:** 5 minutes  
**Frequency:** Daily before business hours

```bash
#!/bin/bash
# Daily health check script

echo "=== DataForge Daily Health Check ==="
echo "Time: $(date)"

# 1. Check application status
echo -e "\n[1/6] Application Status"
systemctl is-active dataforge && echo "✓ Application running" || echo "✗ Application down"

# 2. Check database connectivity
echo -e "\n[2/6] Database Status"
psql -U dataforge_user -d dataforge -c "SELECT 1" > /dev/null 2>&1 && echo "✓ Database connected" || echo "✗ Database error"

# 3. Check Redis connectivity
echo -e "\n[3/6] Cache Status"
redis-cli ping > /dev/null 2>&1 && echo "✓ Redis connected" || echo "✗ Redis error"

# 4. Check API health
echo -e "\n[4/6] API Health"
curl -s https://api.yourdomain.com/health | grep "healthy" > /dev/null && echo "✓ API healthy" || echo "✗ API health issue"

# 5. Check disk usage
echo -e "\n[5/6] Disk Usage"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "⚠ Disk usage: ${DISK_USAGE}% (WARNING)"
else
    echo "✓ Disk usage: ${DISK_USAGE}%"
fi

# 6. Check recent errors
echo -e "\n[6/6] Recent Errors (last hour)"
ERROR_COUNT=$(grep "ERROR\|CRITICAL" /var/log/dataforge/error.log | grep "$(date +%Y-%m-%d\ %H):" | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠ Found $ERROR_COUNT errors in last hour"
    grep "ERROR\|CRITICAL" /var/log/dataforge/error.log | tail -5
else
    echo "✓ No errors detected"
fi

echo -e "\n=== Health Check Complete ==="
```

### Mid-Day Monitoring (12:00 PM)

**Duration:** 2 minutes  
**Frequency:** Daily

```bash
# Quick service check
systemctl status dataforge | grep "active (running)"
systemctl status postgresql | grep "active (running)"
systemctl status redis-server | grep "active (running)"
systemctl status nginx | grep "active (running)"

# Check active connections
psql -U dataforge_user -d dataforge -c "SELECT count(*) as active_connections FROM pg_stat_activity;"
redis-cli info stats | grep connected_clients

# Check requests per minute
tail -100 /var/log/nginx/dataforge_access.log | wc -l
```

### End-of-Day Verification (5:00 PM)

**Duration:** 5 minutes  
**Frequency:** Daily

```bash
# Backup verification
ls -lh /backups/postgresql/ | tail -1

# Log rotation check
ls -lh /var/log/dataforge/ | grep "$(date +%Y-%m-%d)"

# Incident check
grep "CRITICAL\|ERROR" /var/log/dataforge/error.log | wc -l

# Performance summary
curl -s https://api.yourdomain.com/metrics | grep "response_time_seconds" | head -5
```

---

## Monitoring & Alerting

### Key Metrics to Monitor

| Metric               | Normal Range | Warning | Critical |
| -------------------- | ------------ | ------- | -------- |
| API Response Time    | <100ms       | >200ms  | >500ms   |
| Error Rate           | <0.1%        | >1%     | >5%      |
| Database Query Time  | <50ms        | >100ms  | >500ms   |
| Cache Hit Rate       | >95%         | 80-95%  | <80%     |
| Memory Usage         | <60%         | 70-80%  | >80%     |
| CPU Usage            | <50%         | 70-80%  | >80%     |
| Disk Usage           | <60%         | 75%     | >85%     |
| Database Connections | <50          | 100     | 150      |

### Setting Up Prometheus Alerts

```yaml
# /opt/prometheus/alerts.yml

groups:
  - name: dataforge_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # High response time
      - alert: SlowResponses
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        annotations:
          summary: "Slow API responses"
          description: "P95 response time is {{ $value | humanizeDuration }}"

      # Database connection limit
      - alert: HighDatabaseConnections
        expr: pg_stat_activity_count > 150
        for: 5m
        annotations:
          summary: "High database connection count"
          description: "Active connections: {{ $value }}"

      # Disk space low
      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes < 0.15
        for: 5m
        annotations:
          summary: "Low disk space"
          description: "Only {{ $value | humanizePercentage }} free"

      # Cache hit rate low
      - alert: LowCacheHitRate
        expr: redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) < 0.8
        for: 10m
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
```

### Setting Up Email Alerts

```bash
# Install Alertmanager
sudo apt-get install -y alertmanager

# Configure email
sudo tee /etc/alertmanager/config.yml << 'EOF'
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'app-password'
  smtp_from: 'alerts@yourdomain.com'

route:
  receiver: 'ops-team'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'ops-team'
    email_configs:
      - to: 'ops@yourdomain.com'
        from: 'alerts@yourdomain.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'app-password'
        headers:
          Subject: 'DataForge Alert: {{ .GroupLabels.alertname }}'
EOF

sudo systemctl restart alertmanager
```

---

## Maintenance Tasks

### Weekly Maintenance (Friday 2:00 AM)

#### Backup Verification

```bash
# Check backup status
sudo -i
ls -lh /backups/postgresql/ | tail -7

# Test backup restore (in staging)
LATEST_BACKUP=$(ls -t /backups/postgresql/*.sql.gz | head -1)
gunzip -c "$LATEST_BACKUP" | psql -U dataforge_user -d dataforge_test

echo "✓ Backup verification complete"
exit
```

#### Log Analysis

```bash
# Weekly error summary
grep "ERROR" /var/log/dataforge/error.log | wc -l
grep "ERROR" /var/log/dataforge/error.log | cut -d: -f4- | sort | uniq -c | sort -rn | head -10

# Performance summary
tail -10000 /var/log/nginx/dataforge_access.log | \
  awk '{print $(NF-1)}' | \
  sed 's/ms//' | \
  awk '{sum+=$1; count++} END {print "Avg response: " sum/count "ms"}'
```

#### Database Maintenance

```bash
# Vacuum and analyze
psql -U dataforge_user -d dataforge << 'EOF'
VACUUM ANALYZE;
REINDEX DATABASE dataforge;
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF
```

#### Cache Cleanup

```bash
# Check cache memory
redis-cli info memory | grep used_memory_human

# Clear expired sessions
redis-cli EVAL "return redis.call('del', unpack(redis.call('keys', 'session:*')))" 0

# Check cache statistics
redis-cli info stats | grep -E "hits|misses|evictions"
```

### Monthly Maintenance (1st Sunday at 3:00 AM)

#### Full Database Backup & Verification

```bash
# Create monthly backup
mkdir -p /backups/monthly
DATE=$(date +%Y-%m)
pg_dump -U dataforge_user -h localhost dataforge | gzip > /backups/monthly/dataforge_$DATE.sql.gz

# Verify backup integrity
gunzip -t /backups/monthly/dataforge_$DATE.sql.gz && echo "✓ Backup integrity verified"

# Test restore on staging
createdb dataforge_staging
gunzip -c /backups/monthly/dataforge_$DATE.sql.gz | psql -U dataforge_user -d dataforge_staging
psql -U dataforge_user -d dataforge_staging -c "SELECT COUNT(*) as total_records FROM data;"
dropdb dataforge_staging
```

#### Security Audit

```bash
# Check failed login attempts
grep "failed_login\|invalid_password" /var/log/dataforge/error.log | wc -l

# Check anomalies
grep "ANOMALY\|SUSPICIOUS" /var/log/dataforge/audit.log | tail -20

# Verify encryption keys haven't been exposed
grep "ENCRYPTION_KEY" /var/log/ -r && echo "⚠ WARNING: Key exposed in logs"

# Check SSL certificate expiration
echo | openssl s_client -servername api.yourdomain.com -connect api.yourdomain.com:443 2>/dev/null | \
  openssl x509 -noout -dates
```

#### Dependency Updates

```bash
# Check for security updates
pip list --outdated

# Update non-critical packages
pip install --upgrade certifi urllib3

# Test after updates
systemctl restart dataforge
curl -s https://api.yourdomain.com/health | grep healthy
```

---

## Incident Response

### Template: Incident Report

```
INCIDENT REPORT
===============

Incident ID: INC-2025-001
Date/Time: 2025-11-21 14:30 UTC
Severity: CRITICAL

1. DETECTION
   - Detected by: Alert / Manual discovery
   - Detection time: [timestamp]
   - Time to detection: [minutes]

2. IMPACT
   - Services affected: [list]
   - Users impacted: [number/percentage]
   - Duration: [minutes]
   - Business impact: [description]

3. ROOT CAUSE
   - Analysis: [what happened]
   - Contributing factors: [list]
   - Primary cause: [cause]

4. RESOLUTION
   - Actions taken: [list with timestamps]
   - Time to resolution: [minutes]
   - Validation: [how verified]

5. PREVENTION
   - Process changes: [list]
   - Code changes: [list]
   - Monitoring improvements: [list]
   - Target implementation: [date]

6. FOLLOW-UP
   - Scheduled review: [date]
   - Assigned owner: [name]
   - Related incidents: [list]
```

### Scenario 1: Application Crash

**Time to Resolution Target:** 5 minutes

```bash
# Step 1: Verify issue (30 seconds)
curl -s https://api.yourdomain.com/health
systemctl status dataforge | grep "active"

# Step 2: Restart application (1 minute)
sudo systemctl restart dataforge

# Step 3: Verify recovery (30 seconds)
sleep 10
curl -s https://api.yourdomain.com/health | jq .
systemctl status dataforge

# Step 4: Check logs (1 minute)
sudo journalctl -u dataforge -n 50 | grep -i "error\|exception\|crashed"

# Step 5: Notify team if not resolved (5 minutes)
# If still down, escalate to database team and check database logs
psql -U dataforge_user -d dataforge -c "SELECT 1" || sudo systemctl restart postgresql

# Step 6: Post-incident
# 1. Document error in incident report
# 2. Review what caused crash
# 3. Schedule improvement task
```

### Scenario 2: Database Unavailable

**Time to Resolution Target:** 10 minutes

```bash
# Step 1: Verify issue (1 minute)
psql -U dataforge_user -h localhost -d dataforge -c "SELECT 1"
systemctl status postgresql

# Step 2: Check database status (1 minute)
sudo -i -u postgres
psql -c "\conninfo"
psql -d dataforge -c "SELECT pid, state FROM pg_stat_activity LIMIT 10;"

# Step 3: Check disk space (if full) (1 minute)
df -h /var/lib/postgresql/

# Step 4: Restart if needed (1 minute)
sudo systemctl restart postgresql
sleep 5

# Step 5: Verify recovery (1 minute)
psql -U dataforge_user -d dataforge -c "SELECT COUNT(*) FROM data;"

# Step 6: Restart application (1 minute)
sudo systemctl restart dataforge

# Step 7: Monitor recovery (2 minutes)
curl -s https://api.yourdomain.com/health
tail -f /var/log/dataforge/error.log
```

### Scenario 3: High CPU Usage

**Time to Resolution Target:** 15 minutes

```bash
# Step 1: Identify high CPU process (2 minutes)
top -b -n 1 | head -15
ps aux --sort=-%cpu | head -10

# Step 2: Check application load (2 minutes)
curl -s https://api.yourdomain.com/metrics | grep "dataforge_requests_total" | head -5
tail -100 /var/log/nginx/dataforge_access.log | wc -l

# Step 3: Check if specific endpoint causing issue (2 minutes)
tail -1000 /var/log/nginx/dataforge_access.log | \
  awk '{print $7}' | sort | uniq -c | sort -rn | head -10

# Step 4: Temporary mitigation - increase workers if not maxed (3 minutes)
systemctl show dataforge -p ExecStart | grep -o "workers [0-9]*"

# Step 5: Rate limit if under attack (2 minutes)
# Check nginx config and lower limits temporarily
sudo nginx -s reload

# Step 6: Check for slow queries (2 minutes)
psql -U dataforge_user -d dataforge << 'EOF'
SELECT query, mean_time, calls FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 10;
EOF

# Step 7: Kill long-running queries if necessary
psql -U dataforge_user -d dataforge << 'EOF'
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE duration > interval '5 minutes';
EOF
```

### Scenario 4: Memory Leak

**Time to Resolution Target:** 30 minutes

```bash
# Step 1: Confirm memory growth (3 minutes)
watch -n 5 'ps aux | grep dataforge | grep -v grep'

# Step 2: Restart application as temporary fix (2 minutes)
sudo systemctl restart dataforge
free -h
```

Step 3: Enable memory monitoring (3 minutes)

```python
# Add to app.py for next release
import tracemalloc
tracemalloc.start()

# Periodically log memory usage
import psutil
process = psutil.Process()
mem_info = process.memory_info()
logger.info(f"Memory: {mem_info.rss / 1024 / 1024:.1f}MB")
```

Step 4: Review recent code changes (5 minutes)

```bash
git log --oneline -10
git diff HEAD~5 -- app/

# Look for:
# - Circular references
# - Unfinished generators
# - Unbounded caches
```

### Scenario 5: Data Corruption

**Time to Resolution Target:** 1 hour (CRITICAL)

```bash
# Step 1: Stop application immediately (1 minute)
sudo systemctl stop dataforge

# Step 2: Create backup of corrupted database (2 minutes)
sudo -i -u postgres
pg_dump dataforge > /backups/corruption_backup_$(date +%s).sql

# Step 3: Restore from latest good backup (10 minutes)
BACKUP_FILE=$(ls -t /backups/postgresql/*.sql.gz | head -1)
dropdb dataforge
createdb dataforge
gunzip -c "$BACKUP_FILE" | psql -d dataforge

# Step 4: Verify data integrity (5 minutes)
psql -d dataforge << 'EOF'
-- Check record counts
SELECT count(*) as total_records FROM data;

-- Check for NULL in required fields
SELECT count(*) as null_ids FROM data WHERE id IS NULL;

-- Check data types
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'data';
EOF

# Step 5: Restart application (2 minutes)
sudo systemctl start dataforge

# Step 6: Verify restored data (5 minutes)
curl -s https://api.yourdomain.com/health
curl -s https://api.yourdomain.com/data?limit=1 | jq .

# Step 7: Notify users of data loss (5 minutes)
# [Send status update email]

# Step 8: Investigate root cause (remaining time)
# - Check application logs before corruption
# - Review database transaction logs
# - Check for failed migrations
```

---

## Performance Tuning

### Database Query Optimization

```bash
# Identify slow queries
psql -U dataforge_user -d dataforge << 'EOF'
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 20;
EOF

# Enable query planning
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM data WHERE user_id = 123;

# Create missing indexes
CREATE INDEX idx_data_user_id ON data(user_id);
CREATE INDEX idx_data_created_at ON data(created_at DESC);
CREATE INDEX idx_data_encrypted_field ON data(encrypted_field) WHERE is_sensitive = true;

# Analyze index effectiveness
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY tablename, indexname;
```

### Application Performance Tuning

```bash
# Increase worker processes
# Edit: /etc/systemd/system/dataforge.service
# Change: --workers 4 → --workers 8 (for 8-core system)
# Formula: (2 * CPU_COUNT) + 1

# Increase connection pool
# Edit: .env
# DATABASE_POOL_SIZE=20
# DATABASE_POOL_PRE_PING=true

# Optimize caching
# Edit: app/config.py
# CACHE_TTL = 3600  # Increase default TTL
# CACHE_MAX_SIZE = 1000  # Larger cache

# Enable compression
# Edit: /etc/nginx/sites-available/dataforge
# gzip on;
# gzip_types text/plain application/json;
# gzip_min_length 1000;
```

### Monitoring Performance

```bash
# Track API response times
curl -w "%{time_total}\n" -o /dev/null -s https://api.yourdomain.com/health

# Monitor Nginx connection count
netstat -an | grep ESTABLISHED | wc -l

# Check database slow query log
tail -100 /var/log/postgresql/postgresql-13-main.log | grep "duration"

# Monitor Redis memory usage
redis-cli info memory | grep used_memory_human
redis-cli keys '*' | wc -l  # number of cached items
```

---

## Backup & Recovery

### Backup Schedule

| Type    | Frequency       | Retention | Storage         |
| ------- | --------------- | --------- | --------------- |
| Hourly  | Every hour      | 24 hours  | Local SSD       |
| Daily   | 02:00 AM        | 30 days   | Local + Cloud   |
| Weekly  | Sunday 01:00 AM | 12 weeks  | Cloud           |
| Monthly | 1st of month    | 12 months | Cloud + Archive |

### Restore Procedures

#### Quick Restore (Last 24 hours)

```bash
# Find backup
ls -lh /backups/postgresql/ | grep $(date +%Y-%m-%d)

# Stop application
sudo systemctl stop dataforge

# Restore
BACKUP_FILE=$(ls -t /backups/postgresql/*$(date +%Y-%m-%d)* | head -1)
dropdb dataforge
createdb dataforge
gunzip -c "$BACKUP_FILE" | psql -d dataforge

# Restart
sudo systemctl start dataforge
```

#### Full Restore (Any time)

```bash
# Connect to staging server
ssh user@staging-server

# Download backup from cloud
aws s3 cp s3://dataforge-backups/monthly/dataforge_2025-11.sql.gz .

# Restore
gunzip -c dataforge_2025-11.sql.gz | psql -d dataforge_staging

# Run data validation
./scripts/validate_restore.sh dataforge_staging

# If valid, point application to staging
```

---

**Runbook Version:** 5.1  
**Last Updated:** November 21, 2025
