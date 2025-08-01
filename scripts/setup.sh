#!/bin/bash

# =================================================================
# QaAI Legal Assistant System - Initial Setup Script
# =================================================================
# 
# This script sets up the QaAI system for first-time deployment
# 
# Usage: ./scripts/setup.sh [environment]
#
# What this script does:
#   1. Creates necessary directories
#   2. Sets up environment configuration
#   3. Initializes SSL certificates (for production)
#   4. Configures monitoring stack
#   5. Sets up backup directories
#   6. Creates systemd service files (for production)
#
# =================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-development}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
    esac
}

# Check if running as root for production setup
check_permissions() {
    if [[ "$ENVIRONMENT" == "production" && $EUID -ne 0 ]]; then
        log "ERROR" "Production setup requires root privileges"
        log "INFO" "Please run: sudo ./scripts/setup.sh production"
        exit 1
    fi
}

# Create directory structure
create_directories() {
    log "INFO" "Creating directory structure..."
    
    local directories=(
        "data/files"
        "data/index"
        "logs"
        "docker/nginx/ssl"
        "docker/prometheus"
        "docker/grafana/dashboards"
        "docker/grafana/datasources"
        "docker/init-scripts"
        "docker/backup"
    )
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        directories+=(
            "/opt/qaai/data"
            "/opt/qaai/postgres"
            "/opt/qaai/redis"
            "/opt/qaai/prometheus"
            "/opt/qaai/grafana"
            "/opt/qaai/loki"
            "/opt/qaai/backups"
            "/opt/qaai/logs"
            "/var/log/qaai"
        )
    fi
    
    for dir in "${directories[@]}"; do
        if [[ "$dir" == /* ]]; then
            # Absolute path - for production directories
            mkdir -p "$dir"
            if [[ "$ENVIRONMENT" == "production" ]]; then
                chown -R 1000:1000 "$dir" 2>/dev/null || true
            fi
        else
            # Relative path - for project directories
            mkdir -p "$PROJECT_ROOT/$dir"
        fi
        log "INFO" "Created directory: $dir"
    done
}

# Setup environment configuration
setup_environment() {
    log "INFO" "Setting up environment configuration..."
    
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        log "INFO" "Created .env file from .env.example"
        log "WARN" "Please edit .env file with your API keys and configuration"
    else
        log "INFO" ".env file already exists"
    fi
    
    # Set appropriate APP_ENV
    if [[ "$ENVIRONMENT" == "production" ]]; then
        sed -i 's/APP_ENV=development/APP_ENV=production/' "$PROJECT_ROOT/.env"
        sed -i 's/DEBUG_MODE=true/DEBUG_MODE=false/' "$PROJECT_ROOT/.env"
        log "INFO" "Updated .env for production environment"
    fi
}

# Generate SSL certificates for production
setup_ssl() {
    if [[ "$ENVIRONMENT" != "production" ]]; then
        return
    fi
    
    log "INFO" "Setting up SSL certificates for production..."
    
    local ssl_dir="$PROJECT_ROOT/docker/nginx/ssl"
    
    if [[ ! -f "$ssl_dir/cert.pem" || ! -f "$ssl_dir/key.pem" ]]; then
        log "INFO" "Generating self-signed SSL certificate for development..."
        log "WARN" "For production, please replace with proper SSL certificates"
        
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$ssl_dir/key.pem" \
            -out "$ssl_dir/cert.pem" \
            -subj "/C=AE/ST=Dubai/L=DIFC/O=QaAI/CN=localhost"
        
        log "INFO" "Self-signed SSL certificate generated"
        log "WARN" "Remember to replace with production certificates before going live"
    else
        log "INFO" "SSL certificates already exist"
    fi
}

# Setup monitoring configuration
setup_monitoring() {
    log "INFO" "Setting up monitoring configuration..."
    
    # Prometheus configuration
    cat > "$PROJECT_ROOT/docker/prometheus/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'qaai-api'
    static_configs:
      - targets: ['qaai-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'qaai-web'
    static_configs:
      - targets: ['qaai-web:3000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['host.docker.internal:9100']
EOF

    # Grafana datasource configuration
    cat > "$PROJECT_ROOT/docker/grafana/datasources/prometheus.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

    # Basic Grafana dashboard
    cat > "$PROJECT_ROOT/docker/grafana/dashboards/qaai-dashboard.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "QaAI System Dashboard",
    "tags": ["qaai"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])",
            "legendFormat": "Average Response Time"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
EOF

    log "INFO" "Monitoring configuration created"
}

# Setup database initialization script
setup_database() {
    log "INFO" "Setting up database initialization..."
    
    cat > "$PROJECT_ROOT/docker/init-scripts/01-init-qaai.sql" << 'EOF'
-- QaAI Database Initialization Script
-- This script is automatically run when PostgreSQL container starts

-- Create QaAI database and user if they don't exist
SELECT 'CREATE DATABASE qaai'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'qaai');

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set up proper permissions
GRANT ALL PRIVILEGES ON DATABASE qaai TO qaai_user;

-- Create tables (will be handled by application on first run)
\echo 'QaAI database initialization completed'
EOF

    log "INFO" "Database initialization script created"
}

# Setup backup configuration
setup_backup() {
    if [[ "$ENVIRONMENT" != "production" ]]; then
        return
    fi
    
    log "INFO" "Setting up backup configuration..."
    
    # Backup script
    cat > "$PROJECT_ROOT/docker/backup/backup.sh" << 'EOF'
#!/bin/bash

# QaAI Backup Script
# Runs daily via cron to backup application data

set -euo pipefail

BACKUP_DIR="/backup/output"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_PATH="$BACKUP_DIR/qaai_backup_$TIMESTAMP"

mkdir -p "$BACKUP_PATH"

# Backup application data
if [[ -d "/backup/data" ]]; then
    tar -czf "$BACKUP_PATH/data.tar.gz" -C /backup data/
fi

# Backup PostgreSQL database
if command -v pg_dump &> /dev/null; then
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h postgres -U qaai_user qaai > "$BACKUP_PATH/postgres_backup.sql"
fi

# Backup Redis data
if [[ -d "/backup/redis" ]]; then
    cp -r /backup/redis "$BACKUP_PATH/"
fi

# Create backup manifest
cat > "$BACKUP_PATH/manifest.txt" << MANIFEST
QaAI Backup
Created: $(date)
Data: $(du -sh "$BACKUP_PATH/data.tar.gz" 2>/dev/null | cut -f1 || echo "N/A")
Database: $(du -sh "$BACKUP_PATH/postgres_backup.sql" 2>/dev/null | cut -f1 || echo "N/A")
Redis: $(du -sh "$BACKUP_PATH/redis" 2>/dev/null | cut -f1 || echo "N/A")
MANIFEST

# Keep only last 7 backups
find "$BACKUP_DIR" -name "qaai_backup_*" -type d | sort -r | tail -n +8 | xargs rm -rf

echo "Backup completed: $BACKUP_PATH"
EOF

    # Cron job for backups
    cat > "$PROJECT_ROOT/docker/backup/crontab" << 'EOF'
# QaAI Backup Cron Jobs
# Runs daily at 2 AM
0 2 * * * /backup/scripts/backup.sh >> /var/log/backup.log 2>&1

# Cleanup old logs weekly
0 0 * * 0 find /var/log -name "*.log" -mtime +30 -delete
EOF

    chmod +x "$PROJECT_ROOT/docker/backup/backup.sh"
    log "INFO" "Backup configuration created"
}

# Setup systemd service (for production)
setup_systemd() {
    if [[ "$ENVIRONMENT" != "production" ]]; then
        return
    fi
    
    log "INFO" "Setting up systemd service..."
    
    cat > "/etc/systemd/system/qaai.service" << EOF
[Unit]
Description=QaAI Legal Assistant System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable qaai.service
    
    log "INFO" "Systemd service configured"
    log "INFO" "Use 'systemctl start qaai' to start the service"
}

# Setup log rotation
setup_logrotate() {
    if [[ "$ENVIRONMENT" != "production" ]]; then
        return
    fi
    
    log "INFO" "Setting up log rotation..."
    
    cat > "/etc/logrotate.d/qaai" << 'EOF'
/opt/qaai/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root root
    postrotate
        docker kill -s USR1 qaai-api-prod 2>/dev/null || true
        docker kill -s USR1 qaai-web-prod 2>/dev/null || true
    endscript
}

/var/log/qaai/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 root root
}
EOF

    log "INFO" "Log rotation configured"
}

# Final setup instructions
show_next_steps() {
    log "INFO" "Setup completed successfully!"
    echo
    log "INFO" "Next steps:"
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log "INFO" "1. Edit .env file with your production API keys and configuration"
        log "INFO" "2. Replace self-signed SSL certificates with production certificates"
        log "INFO" "3. Configure firewall rules for ports 80, 443, 8000"
        log "INFO" "4. Run deployment script: ./scripts/deploy.sh production --backup"
        log "INFO" "5. Start systemd service: systemctl start qaai"
    else
        log "INFO" "1. Edit .env file with your API keys"
        log "INFO" "2. Run development setup: docker-compose up --build"
        log "INFO" "3. Access application at http://localhost:3000"
    fi
    
    echo
    log "INFO" "For more information, see README.md and docs/API.md"
}

# Main execution
main() {
    log "INFO" "Starting QaAI setup for $ENVIRONMENT environment"
    
    check_permissions
    create_directories
    setup_environment
    setup_ssl
    setup_monitoring
    setup_database
    setup_backup
    setup_systemd
    setup_logrotate
    show_next_steps
    
    log "INFO" "Setup script completed successfully!"
}

# Run main function
main "$@"