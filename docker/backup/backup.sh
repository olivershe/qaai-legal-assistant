#!/bin/bash
# QaAI Production Backup Script
# Runs inside the backup container to create system backups

set -euo pipefail

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/output"
RETENTION_DAYS=30

echo "Starting QaAI backup process at $(date)"

# Create backup directory structure
mkdir -p "$BACKUP_DIR/database"
mkdir -p "$BACKUP_DIR/data"
mkdir -p "$BACKUP_DIR/redis"

# Backup PostgreSQL database
echo "Backing up PostgreSQL database..."
pg_dump -h postgres -U qaai_user -d qaai | gzip > "$BACKUP_DIR/database/qaai_db_$BACKUP_DATE.sql.gz"

# Backup application data
echo "Backing up application data..."
tar -czf "$BACKUP_DIR/data/qaai_data_$BACKUP_DATE.tar.gz" -C /backup/data .

# Backup Redis data (if needed)
echo "Backing up Redis data..."
tar -czf "$BACKUP_DIR/redis/qaai_redis_$BACKUP_DATE.tar.gz" -C /backup/redis .

# Create backup manifest
cat > "$BACKUP_DIR/backup_manifest_$BACKUP_DATE.json" << EOF
{
  "backup_date": "$(date -Iseconds)",
  "backup_id": "$BACKUP_DATE",
  "files": {
    "database": "database/qaai_db_$BACKUP_DATE.sql.gz",
    "data": "data/qaai_data_$BACKUP_DATE.tar.gz", 
    "redis": "redis/qaai_redis_$BACKUP_DATE.tar.gz"
  },
  "sizes": {
    "database": "$(stat -c%s "$BACKUP_DIR/database/qaai_db_$BACKUP_DATE.sql.gz" 2>/dev/null || echo 0)",
    "data": "$(stat -c%s "$BACKUP_DIR/data/qaai_data_$BACKUP_DATE.tar.gz" 2>/dev/null || echo 0)",
    "redis": "$(stat -c%s "$BACKUP_DIR/redis/qaai_redis_$BACKUP_DATE.tar.gz" 2>/dev/null || echo 0)"
  }
}
EOF

# Clean up old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "qaai_*" -type f -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully at $(date)"
echo "Backup files:"
ls -la "$BACKUP_DIR"/*$BACKUP_DATE*