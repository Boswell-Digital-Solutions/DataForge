# DataForge Deployment Guide

**Version:** 5.1  
**Last Updated:** November 21, 2025

---

## Pre-Deployment Checklist

### Infrastructure Requirements

- [ ] Linux server (Ubuntu 20.04+ or CentOS 8+)
- [ ] Minimum 4 GB RAM (8 GB recommended for production)
- [ ] 50 GB SSD storage (100 GB+ for databases)
- [ ] 2+ CPU cores (4+ cores recommended)
- [ ] Outbound internet access for package downloads
- [ ] Inbound ports: 80 (HTTP), 443 (HTTPS), 5432 (PostgreSQL - internal)

### Software Requirements

- [ ] Python 3.10+
- [ ] PostgreSQL 13+
- [ ] Redis 6+
- [ ] Nginx 1.20+ (or HAProxy 2.0+)
- [ ] systemd (process management)

### Security Preparation

- [ ] Generate SSL/TLS certificates
- [ ] Create service user accounts
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Prepare encryption keys
- [ ] Setup backup storage

---

## Step 1: System Setup

### 1.1 Update System

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev
sudo apt-get install -y curl wget git nano

# CentOS
sudo yum update -y
sudo yum groupinstall -y "Development Tools"
sudo yum install -y openssl-devel libffi-devel python3-devel curl wget git nano
```

### 1.2 Create Service User

```bash
# Create dedicated user for application
sudo useradd -m -s /bin/bash dataforge
sudo usermod -aG sudo dataforge

# Setup home directory
sudo mkdir -p /home/dataforge/.config
sudo chown -R dataforge:dataforge /home/dataforge
```

### 1.3 Configure Firewall

```bash
# Enable firewall
sudo ufw enable

# Allow SSH (keep existing)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow PostgreSQL (internal only)
sudo ufw allow from 127.0.0.1 to any port 5432

# Verify
sudo ufw status
```

---

## Step 2: Install PostgreSQL

### 2.1 Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt-get install -y postgresql-13 postgresql-contrib-13

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2.2 Create Database

```bash
# Switch to postgres user
sudo -i -u postgres

# Create database
createdb dataforge

# Create user
createuser --interactive
# Name: dataforge_user
# Superuser: n
# Can create DB: n
# Can create roles: n

# Set password
psql -c "ALTER USER dataforge_user WITH PASSWORD 'secure_password_here';"

# Exit
exit
```

### 2.3 Configure PostgreSQL

```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/13/main/postgresql.conf

# Set these parameters:
# max_connections = 200
# shared_buffers = 256MB
# effective_cache_size = 1GB

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 2.4 Test Connection

```bash
psql -h localhost -U dataforge_user -d dataforge -c "SELECT 1;"
```

---

## Step 3: Install Redis

### 3.1 Install Redis

```bash
# Ubuntu/Debian
sudo apt-get install -y redis-server redis-tools

# Start service
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 3.2 Configure Redis

```bash
# Edit redis.conf
sudo nano /etc/redis/redis.conf

# Set these parameters:
# maxmemory 512mb
# maxmemory-policy allkeys-lru
# appendonly yes

# Restart Redis
sudo systemctl restart redis-server
```

### 3.3 Test Connection

```bash
redis-cli ping
# Output: PONG
```

---

## Step 4: Deploy DataForge

### 4.1 Clone Repository

```bash
# Switch to dataforge user
su - dataforge

# Clone repository
git clone https://github.com/boswecw/DataForge.git
cd DataForge/DataForge
```

### 4.2 Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 4.3 Install Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# Verify installation
python3 -c "import fastapi; print('FastAPI installed')"
```

### 4.4 Configure Environment

```bash
# Create .env file
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://dataforge_user:secure_password_here@localhost:5432/dataforge
SQLALCHEMY_ECHO=False

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_bytes(32).hex())")
MASTER_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Application
DEBUG=False
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# OAuth2 (configure with your providers)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret

# CORS
ALLOWED_ORIGINS=["https://yourdomain.com", "https://api.yourdomain.com"]
EOF

# Secure permissions
chmod 600 .env
```

### 4.5 Run Database Migrations

```bash
# Activate venv first
source venv/bin/activate

# Run migrations
alembic upgrade head

# Verify
psql -U dataforge_user -d dataforge -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"
```

### 4.6 Create Systemd Service

```bash
# Create service file
sudo tee /etc/systemd/system/dataforge.service << 'EOF'
[Unit]
Description=DataForge API Service
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=dataforge
Group=dataforge
WorkingDirectory=/home/dataforge/DataForge/DataForge
Environment="PATH=/home/dataforge/DataForge/DataForge/venv/bin"
ExecStart=/home/dataforge/DataForge/DataForge/venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind unix:/run/dataforge.sock \
    --timeout 60 \
    --access-logfile /var/log/dataforge/access.log \
    --error-logfile /var/log/dataforge/error.log \
    app.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
sudo mkdir -p /var/log/dataforge
sudo chown dataforge:dataforge /var/log/dataforge

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable dataforge
sudo systemctl start dataforge

# Check status
sudo systemctl status dataforge
```

---

## Step 5: Configure Nginx

### 5.1 Install Nginx

```bash
sudo apt-get install -y nginx

# Enable and start
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 5.2 Create Nginx Configuration

```bash
# Create config file
sudo tee /etc/nginx/sites-available/dataforge << 'EOF'
upstream dataforge {
    server unix:/run/dataforge.sock fail_timeout=0;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    client_max_body_size 50M;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    client_max_body_size 50M;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Proxy settings
    location / {
        proxy_pass http://dataforge;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Access logs
    access_log /var/log/nginx/dataforge_access.log combined;
    error_log /var/log/nginx/dataforge_error.log;
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/dataforge /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 5.3 Setup SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d api.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Step 6: Setup Celery (Async Tasks)

### 6.1 Install RabbitMQ

```bash
sudo apt-get install -y rabbitmq-server

# Start and enable
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Create user
sudo rabbitmqctl add_user dataforge_user secure_password
sudo rabbitmqctl set_permissions -p / dataforge_user ".*" ".*" ".*"
```

### 6.2 Create Celery Service

```bash
# Create service file
sudo tee /etc/systemd/system/dataforge-celery.service << 'EOF'
[Unit]
Description=DataForge Celery Worker
After=network.target rabbitmq-server.service

[Service]
Type=forking
User=dataforge
Group=dataforge
WorkingDirectory=/home/dataforge/DataForge/DataForge
Environment="PATH=/home/dataforge/DataForge/DataForge/venv/bin"
ExecStart=/home/dataforge/DataForge/DataForge/venv/bin/celery \
    -A app.tasks.celery \
    worker \
    --loglevel=info \
    --logfile=/var/log/dataforge/celery.log \
    --pidfile=/run/dataforge-celery.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable dataforge-celery
sudo systemctl start dataforge-celery
```

---

## Step 7: Setup Monitoring

### 7.1 Install Prometheus

```bash
# Create prometheus user
sudo useradd --no-create-home --shell /bin/false prometheus

# Download and install
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar -xzf prometheus-2.40.0.linux-amd64.tar.gz
sudo mv prometheus-2.40.0.linux-amd64 /opt/prometheus

# Create service
sudo tee /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus
After=network.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/opt/prometheus/prometheus --config.file=/opt/prometheus/prometheus.yml
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

### 7.2 Configure Prometheus

```bash
# Edit config
sudo tee /opt/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dataforge'
    static_configs:
      - targets: ['localhost:8000']
EOF

sudo systemctl restart prometheus
```

---

## Step 8: Backup Configuration

### 8.1 Setup Database Backups

```bash
# Create backup directory
sudo mkdir -p /backups/postgresql
sudo chown dataforge:dataforge /backups/postgresql
chmod 700 /backups/postgresql

# Create backup script
cat > /home/dataforge/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/dataforge_$DATE.sql.gz"

pg_dump -U dataforge_user -h localhost dataforge | gzip > "$BACKUP_FILE"

# Keep only 30 days of backups
find $BACKUP_DIR -name "dataforge_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
EOF

chmod +x /home/dataforge/backup_db.sh

# Schedule daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /home/dataforge/backup_db.sh >> /var/log/dataforge/backup.log 2>&1") | crontab -
```

---

## Step 9: Post-Deployment Verification

### 9.1 Health Checks

```bash
# Check application health
curl https://api.yourdomain.com/health

# Expected response:
# {"status": "healthy", "database": "connected", "cache": "connected", "version": "5.1"}

# Check metrics
curl https://api.yourdomain.com/metrics | head -20

# Check logs
sudo journalctl -u dataforge -n 50 -f
```

### 9.2 Test Authentication

```bash
# Test login
curl -X POST https://api.yourdomain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "initial_password"
  }'

# Test data access
curl -X GET https://api.yourdomain.com/data \
  -H "Authorization: Bearer <token>"
```

### 9.3 Verify Encryption

```bash
# Check if data encryption is working
psql -U dataforge_user -d dataforge -c "SELECT * FROM data LIMIT 1 \G" | grep encrypted
```

---

## Production Hardening

### Enable Audit Logging

```bash
# Enable audit logs in PostgreSQL
sudo -i -u postgres
psql -d dataforge << 'EOF'
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();
EOF
exit
```

### Setup Fail2Ban

```bash
sudo apt-get install -y fail2ban

# Create filter
sudo tee /etc/fail2ban/filter.d/dataforge.conf << 'EOF'
[Definition]
failregex = ^<HOST>.* 401.*$
            ^<HOST>.* 403.*$
ignoreregex =
EOF

# Create jail
sudo tee /etc/fail2ban/jail.d/dataforge.conf << 'EOF'
[dataforge]
enabled = true
port = http,https
filter = dataforge
logpath = /var/log/nginx/dataforge_access.log
findtime = 600
maxretry = 5
bantime = 3600
EOF

sudo systemctl restart fail2ban
```

### Configure Log Rotation

```bash
sudo tee /etc/logrotate.d/dataforge << 'EOF'
/var/log/dataforge/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 dataforge dataforge
    sharedscripts
    postrotate
        systemctl reload dataforge > /dev/null 2>&1 || true
    endscript
}
EOF
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u dataforge -n 100

# Verify permissions
ls -la /run/dataforge.sock

# Test manually
cd /home/dataforge/DataForge/DataForge
source venv/bin/activate
python3 -c "from app.main import app; print('App loads OK')"
```

### Database Connection Issues

```bash
# Test connection
psql -U dataforge_user -h localhost -d dataforge -c "SELECT 1;"

# Check PostgreSQL logs
sudo tail -100 /var/log/postgresql/postgresql-13-main.log
```

### High CPU/Memory Usage

```bash
# Monitor processes
top -b -u dataforge -n 1

# Check Nginx connections
netstat -an | grep -E "ESTABLISHED|LISTEN" | wc -l

# Restart services if needed
sudo systemctl restart dataforge
```

---

## Scaling Considerations

### Horizontal Scaling (Multiple Servers)

1. Deploy to additional servers following steps 1-5
2. Point all to same PostgreSQL primary
3. Setup session replication in Redis
4. Use load balancer (HAProxy/AWS ELB)
5. Replicate backups across servers

### Vertical Scaling (Bigger Server)

1. Increase CPU/RAM allocation
2. Update gunicorn worker count: `--workers 8` (for 8 CPU)
3. Increase PostgreSQL max_connections
4. Monitor and adjust caching

---

**Deployment Guide Version:** 5.1  
**Last Updated:** November 21, 2025
