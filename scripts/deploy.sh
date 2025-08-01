#!/bin/bash

# =================================================================
# QaAI Legal Assistant System - Production Deployment Script
# =================================================================
# 
# This script automates the deployment of the QaAI system to production
# 
# Usage:
#   ./scripts/deploy.sh [environment] [options]
#
# Environments:
#   - staging: Deploy to staging environment
#   - production: Deploy to production environment
#
# Options:
#   --backup: Create backup before deployment
#   --no-build: Skip building new images
#   --rollback: Rollback to previous version
#   --dry-run: Show what would be deployed without executing
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - .env file configured with production values
#   - SSL certificates in place (for HTTPS)
#   - Sufficient disk space and memory
#
# =================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE_PROD="$PROJECT_ROOT/docker-compose.prod.yml"
COMPOSE_FILE_DEV="$PROJECT_ROOT/docker-compose.yml"
BACKUP_DIR="/opt/qaai/backups"
LOG_FILE="${LOG_FILE:-/var/log/qaai-deploy.log}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
BACKUP=false
NO_BUILD=false
ROLLBACK=false
DRY_RUN=false
FORCE=false

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message" | tee -a "$LOG_FILE"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message" | tee -a "$LOG_FILE"
            ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Usage information
usage() {
    cat << EOF
QaAI Legal Assistant System - Deployment Script

Usage: $0 [environment] [options]

Environments:
    staging        Deploy to staging environment
    production     Deploy to production environment

Options:
    --backup       Create backup before deployment
    --no-build     Skip building new Docker images
    --rollback     Rollback to previous version
    --dry-run      Show deployment plan without executing
    --force        Force deployment without confirmations
    -h, --help     Show this help message

Examples:
    $0 staging --backup
    $0 production --no-build --dry-run
    $0 production --rollback

Prerequisites:
    - Docker and Docker Compose installed
    - .env file configured for target environment
    - SSL certificates in place for production
    - Sufficient system resources (4GB+ RAM, 10GB+ disk)

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            staging|production)
                ENVIRONMENT="$1"
                shift
                ;;
            --backup)
                BACKUP=true
                shift
                ;;
            --no-build)
                NO_BUILD=true
                shift
                ;;
            --rollback)
                ROLLBACK=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    if [[ -z "$ENVIRONMENT" ]]; then
        log "ERROR" "Environment must be specified (staging or production)"
        usage
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log "ERROR" "Docker is not installed"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log "ERROR" "Docker daemon is not running"
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log "ERROR" "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if .env file exists
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        log "ERROR" ".env file not found. Copy .env.example and configure it."
        exit 1
    fi
    
    # Check system resources
    local available_memory=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
    local available_disk=$(df -BG "$PROJECT_ROOT" | awk 'NR==2{print $4}' | sed 's/G//')
    
    if (( $(echo "$available_memory < 2.0" | bc -l) )); then
        log "WARN" "Low available memory: ${available_memory}GB (recommended: 4GB+)"
    fi
    
    if (( available_disk < 10 )); then
        log "WARN" "Low available disk space: ${available_disk}GB (recommended: 20GB+)"
    fi
    
    log "INFO" "Prerequisites check completed"
}

# Load environment variables
load_env() {
    log "INFO" "Loading environment variables..."
    
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        set -a
        source "$PROJECT_ROOT/.env"
        set +a
        log "INFO" "Environment variables loaded from .env"
    else
        log "ERROR" ".env file not found"
        exit 1
    fi
    
    # Validate required environment variables
    local required_vars=("OPENAI_API_KEY" "ANTHROPIC_API_KEY")
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log "ERROR" "Required environment variable $var is not set"
            exit 1
        fi
    done
}

# Create backup
create_backup() {
    if [[ "$BACKUP" == true ]]; then
        log "INFO" "Creating backup..."
        
        local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
        local backup_path="$BACKUP_DIR/qaai_backup_$backup_timestamp"
        
        mkdir -p "$backup_path"
        
        # Backup data directory
        if [[ -d "/opt/qaai/data" ]]; then
            cp -r /opt/qaai/data "$backup_path/"
            log "INFO" "Data directory backed up"
        fi
        
        # Backup database
        if docker ps | grep -q qaai-postgres; then
            docker exec qaai-postgres-prod pg_dump -U qaai_user qaai > "$backup_path/postgres_backup.sql"
            log "INFO" "PostgreSQL database backed up"
        fi
        
        # Backup configuration
        cp "$PROJECT_ROOT/.env" "$backup_path/"
        cp "$PROJECT_ROOT/docker-compose.prod.yml" "$backup_path/"
        
        # Create backup manifest
        cat > "$backup_path/manifest.txt" << EOF
QaAI Backup Manifest
Created: $(date)
Environment: $ENVIRONMENT
Backup Path: $backup_path
Contents:
- Data directory: $(du -sh "$backup_path/data" 2>/dev/null | cut -f1 || echo "N/A")
- Database dump: $(ls -lh "$backup_path/postgres_backup.sql" 2>/dev/null | awk '{print $5}' || echo "N/A")
- Configuration files: .env, docker-compose.prod.yml
EOF

        log "INFO" "Backup created at $backup_path"
        
        # Keep only last 5 backups
        find "$BACKUP_DIR" -name "qaai_backup_*" -type d | sort -r | tail -n +6 | xargs rm -rf
        log "INFO" "Old backups cleaned up (keeping last 5)"
    fi
}

# Build Docker images
build_images() {
    if [[ "$NO_BUILD" == true ]]; then
        log "INFO" "Skipping image build (--no-build specified)"
        return
    fi
    
    log "INFO" "Building Docker images..."
    
    local compose_file="$COMPOSE_FILE_PROD"
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        compose_file="$COMPOSE_FILE_DEV"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "[DRY RUN] Would build images using: $compose_file"
        return
    fi
    
    docker-compose -f "$compose_file" build --no-cache
    log "INFO" "Docker images built successfully"
}

# Deploy services
deploy_services() {
    log "INFO" "Deploying services..."
    
    local compose_file="$COMPOSE_FILE_PROD"
    if [[ "$ENVIRONMENT" == "staging" ]]; then
        compose_file="$COMPOSE_FILE_DEV"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "[DRY RUN] Would deploy using: $compose_file"
        log "INFO" "[DRY RUN] Services to be deployed:"
        docker-compose -f "$compose_file" config --services
        return
    fi
    
    # Stop existing services gracefully
    log "INFO" "Stopping existing services..."
    docker-compose -f "$compose_file" down --timeout 30
    
    # Start services
    log "INFO" "Starting services..."
    docker-compose -f "$compose_file" up -d
    
    # Wait for services to be healthy
    log "INFO" "Waiting for services to be healthy..."
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker-compose -f "$compose_file" ps | grep -q "healthy"; then
            log "INFO" "Services are healthy"
            break
        fi
        
        sleep 10
        ((attempt++))
        log "INFO" "Waiting for services... (attempt $attempt/$max_attempts)"
    done
    
    if [[ $attempt -eq $max_attempts ]]; then
        log "ERROR" "Services failed to become healthy within expected time"
        exit 1
    fi
}

# Run post-deployment tasks
post_deployment() {
    log "INFO" "Running post-deployment tasks..."
    
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "[DRY RUN] Would run post-deployment tasks"
        return
    fi
    
    # Initialize database if needed
    docker-compose -f "$COMPOSE_FILE_PROD" exec -T qaai-api python -c "
from apps.api.core.database import init_db
import asyncio
asyncio.run(init_db())
print('Database initialized')
"
    
    # Ingest sample corpus if data directory is empty
    if [[ ! -d "/opt/qaai/data/index" || -z "$(ls -A /opt/qaai/data/index)" ]]; then
        log "INFO" "Ingesting sample DIFC corpus..."
        docker-compose -f "$COMPOSE_FILE_PROD" exec -T qaai-api python examples/rag_ingest.py examples/sample_corpus/
    fi
    
    # Run health checks
    log "INFO" "Running health checks..."
    curl -f http://localhost:8000/health || {
        log "ERROR" "API health check failed"
        exit 1
    }
    
    curl -f http://localhost:3000 || {
        log "ERROR" "Web health check failed"
        exit 1
    }
    
    log "INFO" "Post-deployment tasks completed"
}

# Rollback to previous version
rollback() {
    log "INFO" "Rolling back to previous version..."
    
    local latest_backup=$(find "$BACKUP_DIR" -name "qaai_backup_*" -type d | sort -r | head -n 1)
    
    if [[ -z "$latest_backup" ]]; then
        log "ERROR" "No backup found for rollback"
        exit 1
    fi
    
    log "INFO" "Rolling back using backup: $latest_backup"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "INFO" "[DRY RUN] Would rollback using: $latest_backup"
        return
    fi
    
    # Stop current services
    docker-compose -f "$COMPOSE_FILE_PROD" down
    
    # Restore data
    if [[ -d "$latest_backup/data" ]]; then
        rm -rf /opt/qaai/data
        cp -r "$latest_backup/data" /opt/qaai/
        log "INFO" "Data directory restored"
    fi
    
    # Restore database
    if [[ -f "$latest_backup/postgres_backup.sql" ]]; then
        docker-compose -f "$COMPOSE_FILE_PROD" up -d postgres
        sleep 20
        docker exec -i qaai-postgres-prod psql -U qaai_user -d qaai < "$latest_backup/postgres_backup.sql"
        log "INFO" "Database restored"
    fi
    
    # Start services
    docker-compose -f "$COMPOSE_FILE_PROD" up -d
    
    log "INFO" "Rollback completed"
}

# Confirmation prompt
confirm_deployment() {
    if [[ "$FORCE" == true ]]; then
        return
    fi
    
    echo
    log "WARN" "You are about to deploy to $ENVIRONMENT environment"
    log "WARN" "This will:"
    [[ "$BACKUP" == true ]] && log "WARN" "  - Create a backup of current data"
    [[ "$NO_BUILD" == false ]] && log "WARN" "  - Build new Docker images"
    log "WARN" "  - Stop current services"
    log "WARN" "  - Deploy new version"
    log "WARN" "  - Run post-deployment tasks"
    echo
    
    read -p "Do you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "INFO" "Deployment cancelled"
        exit 0
    fi
}

# Display deployment summary
deployment_summary() {
    log "INFO" "Deployment Summary:"
    log "INFO" "  Environment: $ENVIRONMENT"
    log "INFO" "  Backup created: $BACKUP"
    log "INFO" "  Images built: $([ "$NO_BUILD" == true ] && echo "No" || echo "Yes")"
    log "INFO" "  Services deployed: $([ "$DRY_RUN" == true ] && echo "Dry run" || echo "Yes")"
    
    if [[ "$DRY_RUN" == false ]]; then
        log "INFO" "  Application URL: http://localhost:3000"
        log "INFO" "  API URL: http://localhost:8000"
        log "INFO" "  API Documentation: http://localhost:8000/docs"
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            log "INFO" "  Monitoring: http://localhost:3001 (Grafana)"
            log "INFO" "  Metrics: http://localhost:9090 (Prometheus)"
        fi
    fi
}

# Main execution
main() {
    log "INFO" "Starting QaAI deployment script"
    log "INFO" "Environment: $ENVIRONMENT"
    
    parse_args "$@"
    check_prerequisites
    load_env
    
    if [[ "$ROLLBACK" == true ]]; then
        rollback
        log "INFO" "Rollback completed successfully"
        exit 0
    fi
    
    confirm_deployment
    create_backup
    build_images
    deploy_services
    post_deployment
    deployment_summary
    
    log "INFO" "Deployment completed successfully!"
}

# Handle script interruption
trap 'log "ERROR" "Deployment interrupted"; exit 1' INT TERM

# Ensure log file exists and is writable
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Run main function with all arguments
main "$@"