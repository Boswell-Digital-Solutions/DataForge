# DataForge Troubleshooting Guide

**Version:** 5.1  
**Last Updated:** November 21, 2025

---

## Quick Diagnosis Flowchart

```
Application Issue
    ↓
Is application running? (systemctl status dataforge)
├─ YES → Check API endpoint (curl https://api.yourdomain.com/health)
│        ├─ Returns 200 OK → Issue is specific endpoint
│        │                    └─ Go to "API Issues" section
│        └─ Error response → Check application logs
│                           └─ Go to "Log Analysis" section
│
└─ NO → Start application (systemctl start dataforge)
        └─ Still won't start?
           └─ Go to "Application Won't Start" section
```

---

## Application Won't Start

### Symptom: Service fails to start

```bash
# Check service status
sudo systemctl status dataforge

# View detailed error
sudo journalctl -u dataforge -n 50 --no-pager
```

### Root Cause Checklist

#### 1. Port Already in Use (Port 8000)

```bash
# Check if port is in use
sudo lsof -i :8000

# If port is in use, kill process
sudo kill -9 <PID>

# Or change port in /etc/systemd/system/dataforge.service
# ExecStart=...gunicorn --bind 127.0.0.1:8001...

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl start dataforge
```

#### 2. Missing Environment Variables

```bash
# Check .env file exists
ls -la /home/dataforge/DataForge/DataForge/.env

# Verify critical variables are set
grep -E "DATABASE_URL|SECRET_KEY|ENCRYPTION_KEY" .env | wc -l
# Should return 3+

# If missing, add them
echo "DATABASE_URL=postgresql://dataforge_user:password@localhost:5432/dataforge" >> .env
echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env

# Restart
sudo systemctl restart dataforge
```

#### 3. Database Connection Failed

```bash
# Test database connection directly
psql -U dataforge_user -h localhost -d dataforge -c "SELECT 1"

# If connection fails:
# - Check PostgreSQL is running
sudo systemctl status postgresql

# - Check credentials in .env
grep DATABASE_URL .env

# - Verify user exists in PostgreSQL
sudo -i -u postgres
psql -c "\du" | grep dataforge

# - Reset password if needed
psql -c "ALTER USER dataforge_user WITH PASSWORD 'new_password';"
```

#### 4. Python Virtual Environment Issue

```bash
# Check if venv exists
ls -la /home/dataforge/DataForge/DataForge/venv/

# If not, create it
cd /home/dataforge/DataForge/DataForge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart dataforge
```

#### 5. Missing Dependencies

```bash
# Check if requirements installed
source /home/dataforge/DataForge/DataForge/venv/bin/activate
python3 -c "import fastapi; import sqlalchemy; import redis; print('All imports OK')"

# If import fails, reinstall
pip install -r requirements.txt

# Check for corrupted package
pip install --force-reinstall fastapi sqlalchemy redis
```

#### 6. Syntax Error in Code

```bash
# Test Python syntax
python3 -m py_compile app/main.py
python3 -m py_compile app/utils/*.py

# If syntax error, check logs
sudo journalctl -u dataforge -n 100 | grep "SyntaxError"

# Verify last code changes
cd /home/dataforge/DataForge/DataForge
git log --oneline -5
git diff HEAD~1

# Revert if recent bad change
git revert HEAD
sudo systemctl restart dataforge
```

#### 7. Insufficient Permissions

```bash
# Check file permissions
ls -la /home/dataforge/DataForge/DataForge/ | grep -E "^-"

# Fix permissions
sudo chown -R dataforge:dataforge /home/dataforge/DataForge/
sudo chmod -R 750 /home/dataforge/DataForge/

# Check .env file specifically
ls -la /home/dataforge/DataForge/DataForge/.env
# Should be -rw------- (600)

# Check socket directory
ls -la /run/dataforge.sock
# If missing, may be permissions issue with /run

# Restart service
sudo systemctl restart dataforge
```

---

## High Database Latency

### Symptom: Slow database queries, high response times

```bash
# Check database query performance
curl -X GET https://api.yourdomain.com/data?limit=10 -w "\nTime: %{time_total}s\n"
# If > 1 second, database is slow
```

### Diagnosis

#### 1. Check Connection Pool Exhaustion

```bash
# View active connections
psql -U dataforge_user -d dataforge << 'EOF'
SELECT count(*) as active_connections FROM pg_stat_activity;
EOF

# If approaching max_connections (default 100):
# - Check for idle connections
psql -U dataforge_user -d dataforge << 'EOF'
SELECT pid, usename, state, query_start FROM pg_stat_activity
WHERE state = 'idle' AND query_start < now() - interval '1 hour';
EOF

# - Kill idle connections
psql -U dataforge_user -d dataforge << 'EOF'
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'idle' AND query_start < now() - interval '1 hour';
EOF

# - Increase connection pool in .env
echo "DATABASE_POOL_SIZE=50" >> .env
sudo systemctl restart dataforge
```

#### 2. Check for Lock Contention

```bash
# View locks
psql -U dataforge_user -d dataforge << 'EOF'
SELECT * FROM pg_locks WHERE NOT granted;
EOF

# If locks exist, view conflicting statements
psql -U dataforge_user -d dataforge << 'EOF'
SELECT
  a.pid as blocking_pid,
  b.pid as blocked_pid,
  b.query as blocked_query
FROM pg_stat_activity a
JOIN pg_stat_activity b ON a.pid = ANY(pg_blocking_pids(b.pid))
ORDER BY b.query_start;
EOF

# Kill blocking query if necessary
psql -U dataforge_user -d dataforge << 'EOF'
SELECT pg_terminate_backend(<blocking_pid>);
EOF
```

#### 3. Check Missing Indexes

```bash
# Identify slow queries
psql -U dataforge_user -d dataforge << 'EOF'
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 100  -- queries taking > 100ms
ORDER BY mean_time DESC LIMIT 10;
EOF

# Analyze query plan
EXPLAIN ANALYZE SELECT * FROM data WHERE user_id = 123;

# Create missing indexes
CREATE INDEX CONCURRENTLY idx_data_user_id ON data(user_id);
CREATE INDEX CONCURRENTLY idx_data_created_at ON data(created_at DESC);

# Verify index created
SELECT * FROM pg_indexes WHERE tablename = 'data';
```

#### 4. Check Table Bloat

```bash
# View table sizes
psql -U dataforge_user -d dataforge << 'EOF'
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF

# Run vacuum and analyze
VACUUM ANALYZE data;
REINDEX TABLE data;

# For production, use CONCURRENT
VACUUM ANALYZE VERBOSE data;
```

#### 5. Check Disk I/O

```bash
# Monitor disk I/O
iostat -x 1 10

# Check slow disk
df -h /var/lib/postgresql/
# If > 90% full, add more storage

# Monitor query disk reads
psql -U dataforge_user -d dataforge << 'EOF'
SELECT
  schemaname,
  tablename,
  idx_scan as index_scans,
  seq_scan as sequential_scans,
  seq_tup_read as rows_read_sequentially
FROM pg_stat_user_tables
ORDER BY seq_scan DESC;
EOF
```

---

## High Memory Usage

### Symptom: Application consuming 80%+ memory

```bash
# Check memory usage
free -h
ps aux --sort=-%mem | grep dataforge | head -5

# Get detailed breakdown
top -b -n 1 | grep dataforge
```

### Solutions

#### 1. Reduce Connection Pool

```bash
# Current setting
grep DATABASE_POOL_SIZE .env

# Reduce if > 50
sed -i 's/DATABASE_POOL_SIZE=.*/DATABASE_POOL_SIZE=20/' .env

# Restart
sudo systemctl restart dataforge
```

#### 2. Clear Cache

```bash
# View cache size
redis-cli info memory | grep used_memory_human

# Clear expired sessions
redis-cli EVAL "return redis.call('del', unpack(redis.call('keys', 'session:*')))" 0

# Clear all cache (WARNING: affects performance)
redis-cli FLUSHDB

# Set max memory policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG REWRITE
```

#### 3. Reduce Worker Processes

```bash
# Check current workers
grep "\-\-workers" /etc/systemd/system/dataforge.service

# Reduce workers
sudo sed -i 's/--workers [0-9]*/--workers 2/' /etc/systemd/system/dataforge.service

# Restart
sudo systemctl daemon-reload
sudo systemctl restart dataforge
```

#### 4. Check for Memory Leak

```bash
# Monitor memory over time
watch -n 5 'ps aux | grep dataforge | grep -v grep | awk "{print \$6}"'

# If consistently growing:
# - Check application logs for errors
sudo journalctl -u dataforge -n 100 | grep -i "error\|exception\|warning"

# - Review recent code changes
git log --oneline -10

# - Restart application
sudo systemctl restart dataforge

# - Monitor again
watch -n 5 'free -h'
```

---

## Cache Issues (Redis)

### Symptom: Redis connection errors or cache not working

```bash
# Check Redis status
redis-cli ping
# Expected: PONG

# Check if service running
sudo systemctl status redis-server
```

### Solutions

#### 1. Redis Connection Refused

```bash
# Check if Redis is running
sudo systemctl status redis-server

# If not running, start it
sudo systemctl start redis-server

# Check if listening on correct port
netstat -tlnp | grep redis
# Should show port 6379

# Verify .env has correct URL
grep REDIS_URL .env
# Should be: REDIS_URL=redis://localhost:6379

# Test connection
redis-cli -h localhost ping
```

#### 2. High Memory in Redis

```bash
# Check memory usage
redis-cli info memory

# Check number of keys
redis-cli DBSIZE

# Clear old keys
redis-cli EVAL "
for i, key in ipairs(redis.call('KEYS', '*')) do
  if redis.call('TTL', key) < 0 then
    redis.call('DEL', key)
  end
end
return 'Cleared expired keys'
" 0

# If still high, increase max memory
sudo redis-cli CONFIG SET maxmemory 1gb
sudo redis-cli CONFIG REWRITE
```

#### 3. Cache Hit Rate Low

```bash
# Check cache statistics
redis-cli info stats | grep -E "hits|misses|evictions"

# Calculate hit rate
redis-cli EVAL "
local hits = tonumber(redis.call('INFO', 'stats')['keyspace_hits'])
local misses = tonumber(redis.call('INFO', 'stats')['keyspace_misses'])
return hits / (hits + misses)
" 0

# If < 80%, check what's being cached
redis-cli KEYS '*' | head -20

# Check cache TTL
redis-cli TTL <key>
# If -1, key has no expiration
```

---

## API Endpoint Issues

### Symptom: Specific endpoint returns error

```bash
# Test endpoint
curl -v https://api.yourdomain.com/endpoint

# Check response code
curl -w "\n%{http_code}\n" -o /dev/null -s https://api.yourdomain.com/endpoint
```

### Common Errors

#### 401 Unauthorized

```bash
# Missing or invalid token
# Solution: Include Authorization header
curl -H "Authorization: Bearer <token>" https://api.yourdomain.com/data

# Test token validity
curl -X POST https://api.yourdomain.com/auth/token/verify \
  -H "Content-Type: application/json" \
  -d '{"token": "<token>"}'

# Refresh token if expired
curl -X POST https://api.yourdomain.com/auth/token/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

#### 403 Forbidden

```bash
# User lacks permission
# Check user role
curl -H "Authorization: Bearer <token>" \
  https://api.yourdomain.com/auth/me

# Grant permission in database
psql -U dataforge_user -d dataforge << 'EOF'
UPDATE users SET role = 'admin' WHERE email = 'user@example.com';
EOF
```

#### 404 Not Found

```bash
# Endpoint doesn't exist or resource not found
# Verify endpoint is correct
curl https://api.yourdomain.com/data/invalid-id

# Check API documentation
grep "^GET\|^POST" API_REFERENCE.md

# For resource errors, check if resource exists
psql -U dataforge_user -d dataforge << 'EOF'
SELECT id, title FROM data WHERE id = 'resource-id';
EOF
```

#### 429 Rate Limited

```bash
# Too many requests
# Wait before retrying
sleep 60

# Check rate limit headers
curl -i https://api.yourdomain.com/data 2>&1 | grep -i "ratelimit\|x-ratelimit"

# For legitimate high traffic:
# Contact ops team to increase limits in .env
# RATE_LIMIT_REQUESTS=1000
# RATE_LIMIT_PERIOD=3600
```

#### 500 Internal Server Error

```bash
# Application error
# Check logs
sudo journalctl -u dataforge -n 50 | grep ERROR

# Check specific error
tail -100 /var/log/dataforge/error.log | grep "500"

# Check database connection
psql -U dataforge_user -d dataforge -c "SELECT 1"

# Restart application
sudo systemctl restart dataforge

# Test again
curl https://api.yourdomain.com/health
```

---

## Network & Connectivity

### Symptom: Can't reach API, connection timeout

```bash
# Test DNS
nslookup api.yourdomain.com
dig api.yourdomain.com

# Test network reachability
ping api.yourdomain.com
traceroute api.yourdomain.com

# Test port connectivity
curl -v https://api.yourdomain.com
nc -zv api.yourdomain.com 443
```

### Solutions

#### 1. Nginx Not Running

```bash
# Check Nginx
sudo systemctl status nginx

# If not running
sudo systemctl start nginx

# Check Nginx configuration
sudo nginx -t

# View error logs
sudo tail -50 /var/log/nginx/error.log
```

#### 2. Firewall Blocking

```bash
# Check firewall status
sudo ufw status

# Allow ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check specific rule
sudo ufw show added

# If blocked, enable service
sudo ufw enable
```

#### 3. SSL Certificate Issues

```bash
# Check certificate validity
echo | openssl s_client -servername api.yourdomain.com -connect api.yourdomain.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Check certificate expiration
openssl x509 -enddate -noout -in /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem

# If expired, renew
sudo certbot renew --force-renewal

# Reload Nginx
sudo systemctl reload nginx
```

#### 4. Backend Socket Issues

```bash
# Check if backend socket exists
ls -la /run/dataforge.sock

# If missing, application not running
sudo systemctl status dataforge

# Check socket permissions
sudo chown dataforge:www-data /run/dataforge.sock
sudo chmod 660 /run/dataforge.sock

# Restart services
sudo systemctl restart dataforge
sudo systemctl reload nginx
```

---

## Performance Baseline

### Expected Response Times

| Endpoint          | Expected | Slow   | Critical |
| ----------------- | -------- | ------ | -------- |
| /health           | 10ms     | 50ms   | 100ms    |
| /auth/login       | 100ms    | 500ms  | 1000ms   |
| POST /data        | 200ms    | 1000ms | 2000ms   |
| GET /data         | 50ms     | 200ms  | 500ms    |
| GET /data/{id}    | 30ms     | 100ms  | 300ms    |
| DELETE /data/{id} | 100ms    | 500ms  | 1000ms   |

### Check Current Performance

```bash
# Load test (warning: affects live system)
ab -n 100 -c 10 https://api.yourdomain.com/health

# Or use curl in loop
for i in {1..10}; do
  curl -w "%{time_total}\n" -o /dev/null -s https://api.yourdomain.com/data
done | awk '{sum+=$1} END {print "Average: " sum/NR "s"}'

# Check recent response times
tail -1000 /var/log/nginx/dataforge_access.log | \
  awk '{print $(NF-1)}' | sed 's/ms//' | \
  awk '{sum+=$1; count++} END {print "Avg: " sum/count "ms"}'
```

---

## Log File Locations

| Log File     | Location                                   | Purpose           |
| ------------ | ------------------------------------------ | ----------------- |
| Application  | /var/log/dataforge/error.log               | App errors        |
| Access       | /var/log/nginx/dataforge_access.log        | HTTP requests     |
| Database     | /var/log/postgresql/postgresql-13-main.log | DB errors         |
| Systemd      | journalctl -u dataforge                    | Service logs      |
| Nginx errors | /var/log/nginx/error.log                   | Web server errors |
| Audit        | /var/log/dataforge/audit.log               | Security audit    |

---

## Getting Help

### Contact Information

**On-Call Engineer:** (24/7) pager@yourdomain.com  
**Ops Team:** ops@yourdomain.com  
**Documentation:** https://docs.yourdomain.com

### Escalation Path

1. **Level 1:** Follow this troubleshooting guide
2. **Level 2:** Contact ops team (ops@yourdomain.com)
3. **Level 3:** Page on-call engineer if critical
4. **Level 4:** Executive escalation if business impact

### Reporting a Bug

When reporting issues, include:

```
Bug Report Template
===================

Title: [One sentence description]

Severity: [Critical/High/Medium/Low]

Environment:
- OS: [Ubuntu/CentOS/etc]
- Version: [5.1]
- Date: [YYYY-MM-DD HH:MM UTC]

Steps to Reproduce:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Expected: [What should happen]
Actual: [What actually happened]

Error Message: [Full error message]

Logs: [Relevant log snippets]

Impact: [Who/what affected, for how long]
```

---

**Troubleshooting Guide Version:** 5.1  
**Last Updated:** November 21, 2025
