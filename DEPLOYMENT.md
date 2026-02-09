# Deployment Guide

## Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.8 or higher
- Redis 5.0 or higher
- sudo access for installation

## Installation

### 1. System Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and Redis
sudo apt install python3 python3-pip python3-venv redis-server -y

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 2. Application Setup

```bash
# Clone the repository
git clone https://github.com/m-nobin/railwatch-bd.git
cd railwatch-bd

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Required configuration:
```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
TTL_SECONDS=600

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# CORS - Set to your production domains
ALLOWED_ORIGINS=https://train.sportsprime.live

# GitHub Webhook Secret
GITHUB_SECRET=your_secure_secret_here
```

### 4. Data Files

Ensure `data.json` is present and valid:

```bash
# Validate data structure
python3 data_validator.py
```

### 5. Testing

```bash
# Test the application
python3 main.py

# In another terminal, test the API
curl http://localhost:8000/health
```

## Production Deployment

### Option 1: systemd Service (Recommended)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/railwatch-bd.service
```

Service configuration:
```ini
[Unit]
Description=Bangladesh Railway Train Tracking API
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/railwatch-bd
Environment="PATH=/opt/railwatch-bd/venv/bin"
EnvironmentFile=/opt/railwatch-bd/.env
ExecStart=/opt/railwatch-bd/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable railwatch-bd
sudo systemctl start railwatch-bd
sudo systemctl status railwatch-bd
```

### Option 2: Docker (Alternative)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
    restart: unless-stopped
    volumes:
      - ./data.json:/app/data.json:ro
      - ./issue_reports.log:/app/issue_reports.log

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

Deploy with Docker:
```bash
docker-compose up -d
docker-compose logs -f
```

## Reverse Proxy Setup

### nginx Configuration

```nginx
# /etc/nginx/sites-available/railwatch-bd
upstream railwatch_backend {
    server 127.0.0.1:8000;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    listen 80;
    server_name train.sportsprime.live;
    
    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name train.sportsprime.live;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/train.sportsprime.live/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/train.sportsprime.live/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Logging
    access_log /var/log/nginx/railwatch-bd-access.log;
    error_log /var/log/nginx/railwatch-bd-error.log;

    # API endpoints
    location / {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://railwatch_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers (if not handled by app)
        add_header Access-Control-Allow-Origin "https://train.sportsprime.live" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type" always;
    }

    # Health check endpoint (no rate limit)
    location /health {
        proxy_pass http://railwatch_backend;
        proxy_set_header Host $host;
        access_log off;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/railwatch-bd /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d train.sportsprime.live

# Auto-renewal is enabled by default
sudo certbot renew --dry-run
```

## Monitoring and Maintenance

### Log Rotation

Create `/etc/logrotate.d/railwatch-bd`:
```
/opt/railwatch-bd/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload railwatch-bd > /dev/null 2>&1 || true
    endscript
}
```

### Monitoring Scripts

Create monitoring script `/opt/railwatch-bd/monitor.sh`:
```bash
#!/bin/bash

# Check if service is running
if ! systemctl is-active --quiet railwatch-bd; then
    echo "Service is down! Restarting..."
    systemctl restart railwatch-bd
    # Send alert (email, Slack, etc.)
fi

# Check API health
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$RESPONSE" != "200" ]; then
    echo "Health check failed with status $RESPONSE"
    # Send alert
fi

# Check Redis
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Redis is down!"
    systemctl restart redis-server
    # Send alert
fi
```

Add to cron:
```bash
# Check every 5 minutes
*/5 * * * * /opt/railwatch-bd/monitor.sh >> /var/log/railwatch-bd-monitor.log 2>&1
```

### Backup Strategy

Backup Redis data:
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/redis"

mkdir -p $BACKUP_DIR
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_DIR/dump-$DATE.rdb
find $BACKUP_DIR -name "dump-*.rdb" -mtime +30 -delete
```

Backup configuration and logs:
```bash
tar -czf /backup/railwatch-config-$(date +%Y%m%d).tar.gz \
    /opt/railwatch-bd/.env \
    /opt/railwatch-bd/data.json \
    /opt/railwatch-bd/issue_reports.log
```

## Updating the Application

```bash
# Navigate to application directory
cd /opt/railwatch-bd

# Activate virtual environment
source venv/bin/activate

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart railwatch-bd

# Check status
sudo systemctl status railwatch-bd
```

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status railwatch-bd
sudo journalctl -u railwatch-bd -n 50 -f
```

### Check Application Logs
```bash
tail -f /var/log/railwatch-bd/*.log
```

### Check Redis
```bash
redis-cli ping
redis-cli info
redis-cli --scan --pattern "train:*" | wc -l
```

### Check Port Availability
```bash
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :6379
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Get revision
curl http://localhost:8000/initrevision

# Get train positions
curl http://localhost:8000/current/101,102
```

## Performance Tuning

### Redis Optimization

Edit `/etc/redis/redis.conf`:
```conf
# Increase max memory
maxmemory 512mb
maxmemory-policy allkeys-lru

# Enable persistence
save 900 1
save 300 10
save 60 10000

# AOF persistence for durability
appendonly yes
appendfsync everysec
```

### Application Workers

For production, use multiple workers:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Rule of thumb: `workers = (2 x CPU cores) + 1`

### Database (data.json) Optimization

- Keep data.json validated and optimized
- Run `data_validator.py` regularly
- Consider splitting large data files if needed

## Security Hardening

1. **Firewall Configuration:**
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

2. **File Permissions:**
```bash
chmod 600 /opt/railwatch-bd/.env
chmod 640 /opt/railwatch-bd/*.log
chown -R www-data:www-data /opt/railwatch-bd
```

3. **Regular Updates:**
```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Python packages
pip install --upgrade pip
pip list --outdated
```

## Support

For deployment issues:
1. Check logs first
2. Verify configuration
3. Test components individually
4. Open a GitHub issue with details
