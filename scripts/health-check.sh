#!/bin/bash

# =================================================================
# QaAI Legal Assistant System - Health Check Script
# =================================================================
# 
# This script performs comprehensive health checks on the QaAI system
# 
# Usage: ./scripts/health-check.sh [options]
#
# Options:
#   --verbose    Show detailed output
#   --json       Output results in JSON format
#   --timeout N  Set timeout for checks (default: 30 seconds)
#   --fix        Attempt to fix common issues automatically
#
# Exit codes:
#   0: All checks passed
#   1: Some checks failed but system is functional
#   2: Critical failures detected
#
# =================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMEOUT=30
VERBOSE=false
JSON_OUTPUT=false
AUTO_FIX=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check results
declare -A CHECK_RESULTS
declare -A CHECK_MESSAGES
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
CRITICAL_FAILURES=0

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose)
                VERBOSE=true
                shift
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --fix)
                AUTO_FIX=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Usage information
usage() {
    cat << EOF
QaAI Legal Assistant System - Health Check Script

Usage: $0 [options]

Options:
    --verbose       Show detailed output for all checks
    --json          Output results in JSON format
    --timeout N     Set timeout for HTTP checks (default: 30s)
    --fix           Attempt to fix common issues automatically
    -h, --help      Show this help message

Examples:
    $0                          # Basic health check
    $0 --verbose                # Detailed health check
    $0 --json > health.json     # JSON output for monitoring
    $0 --fix --verbose          # Attempt fixes with detailed output

EOF
}

# Logging functions
log() {
    if [[ "$JSON_OUTPUT" == false ]]; then
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
                if [[ "$VERBOSE" == true ]]; then
                    echo -e "${BLUE}[DEBUG]${NC} $message"
                fi
                ;;
        esac
    fi
}

# Record check result
record_check() {
    local check_name="$1"
    local status="$2"
    local message="$3"
    local critical="${4:-false}"
    
    CHECK_RESULTS["$check_name"]="$status"
    CHECK_MESSAGES["$check_name"]="$message"
    
    ((TOTAL_CHECKS++))
    
    if [[ "$status" == "PASS" ]]; then
        ((PASSED_CHECKS++))
        log "INFO" "✓ $check_name: $message"
    else
        ((FAILED_CHECKS++))
        if [[ "$critical" == true ]]; then
            ((CRITICAL_FAILURES++))
            log "ERROR" "✗ $check_name: $message [CRITICAL]"
        else
            log "WARN" "⚠ $check_name: $message"
        fi
    fi
}

# Check if Docker is running
check_docker() {
    log "DEBUG" "Checking Docker status..."
    
    if ! command -v docker &> /dev/null; then
        record_check "docker_installed" "FAIL" "Docker is not installed" true
        return
    fi
    
    if ! docker info &> /dev/null; then
        record_check "docker_running" "FAIL" "Docker daemon is not running" true
        return
    fi
    
    record_check "docker_status" "PASS" "Docker is running"
}

# Check Docker Compose
check_docker_compose() {
    log "DEBUG" "Checking Docker Compose..."
    
    if ! command -v docker-compose &> /dev/null; then
        record_check "docker_compose" "FAIL" "Docker Compose is not installed" true
        return
    fi
    
    record_check "docker_compose" "PASS" "Docker Compose is available"
}

# Check running containers
check_containers() {
    log "DEBUG" "Checking container status..."
    
    local expected_containers=("qaai-api" "qaai-web" "qaai-redis")
    local running_containers=$(docker ps --format "{{.Names}}" | grep "qaai-" || true)
    
    if [[ -z "$running_containers" ]]; then
        record_check "containers_running" "FAIL" "No QaAI containers are running" true
        return
    fi
    
    local missing_containers=()
    for container in "${expected_containers[@]}"; do
        if ! echo "$running_containers" | grep -q "$container"; then
            missing_containers+=("$container")
        fi
    done
    
    if [[ ${#missing_containers[@]} -gt 0 ]]; then
        record_check "containers_running" "FAIL" "Missing containers: ${missing_containers[*]}"
    else
        record_check "containers_running" "PASS" "All required containers are running"
    fi
}

# Check container health
check_container_health() {
    log "DEBUG" "Checking container health status..."
    
    local unhealthy_containers=()
    
    # Check each container's health status
    while IFS= read -r container; do
        if [[ -n "$container" ]]; then
            local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-health-check")
            
            if [[ "$health_status" == "unhealthy" ]]; then
                unhealthy_containers+=("$container")
            fi
            
            log "DEBUG" "Container $container health: $health_status"
        fi
    done <<< "$(docker ps --format "{{.Names}}" | grep "qaai-" || true)"
    
    if [[ ${#unhealthy_containers[@]} -gt 0 ]]; then
        record_check "container_health" "FAIL" "Unhealthy containers: ${unhealthy_containers[*]}"
    else
        record_check "container_health" "PASS" "All containers are healthy"
    fi
}

# Check API endpoint
check_api_endpoint() {
    log "DEBUG" "Checking API endpoint..."
    
    local api_url="http://localhost:8000"
    
    if ! curl -s -f --connect-timeout "$TIMEOUT" "$api_url/health" &> /dev/null; then
        record_check "api_endpoint" "FAIL" "API endpoint not responding at $api_url/health" true
        
        if [[ "$AUTO_FIX" == true ]]; then
            log "INFO" "Attempting to restart API container..."
            docker-compose restart qaai-api &> /dev/null || true
            sleep 10
            
            if curl -s -f --connect-timeout "$TIMEOUT" "$api_url/health" &> /dev/null; then
                record_check "api_restart_fix" "PASS" "API container restart successful"
            else
                record_check "api_restart_fix" "FAIL" "API container restart failed"
            fi
        fi
        return
    fi
    
    # Check API response content
    local api_response=$(curl -s --connect-timeout "$TIMEOUT" "$api_url/health" 2>/dev/null || echo "{}")
    
    if echo "$api_response" | grep -q '"status":"healthy"'; then
        record_check "api_endpoint" "PASS" "API endpoint is healthy"
    else
        record_check "api_endpoint" "FAIL" "API endpoint returned unexpected response"
    fi
}

# Check web frontend
check_web_frontend() {
    log "DEBUG" "Checking web frontend..."
    
    local web_url="http://localhost:3000"
    
    if ! curl -s -f --connect-timeout "$TIMEOUT" "$web_url" &> /dev/null; then
        record_check "web_frontend" "FAIL" "Web frontend not responding at $web_url"
        return
    fi
    
    record_check "web_frontend" "PASS" "Web frontend is accessible"
}

# Check database connectivity
check_database() {
    log "DEBUG" "Checking database connectivity..."
    
    # Check if database container is running
    if ! docker ps | grep -q "qaai-.*postgres\|qaai-.*redis"; then
        record_check "database_container" "FAIL" "Database container not running"
        return
    fi
    
    # Test database connection through API
    local db_check_url="http://localhost:8000/health/db"
    local response=$(curl -s --connect-timeout "$TIMEOUT" "$db_check_url" 2>/dev/null || echo '{"status":"error"}')
    
    if echo "$response" | grep -q '"status":"healthy"'; then
        record_check "database_connection" "PASS" "Database connection is healthy"
    else
        record_check "database_connection" "FAIL" "Database connection issues detected"
    fi
}

# Check Redis cache
check_redis() {
    log "DEBUG" "Checking Redis cache..."
    
    if ! docker ps | grep -q "qaai.*redis"; then
        record_check "redis_container" "FAIL" "Redis container not running"
        return
    fi
    
    # Test Redis connection
    if docker exec qaai-redis-dev redis-cli ping 2>/dev/null | grep -q "PONG"; then
        record_check "redis_connection" "PASS" "Redis is responding"
    else
        record_check "redis_connection" "FAIL" "Redis connection failed"
    fi
}

# Check disk space
check_disk_space() {
    log "DEBUG" "Checking disk space..."
    
    local data_dir="$PROJECT_ROOT/data"
    local available_space=$(df -BG "$data_dir" 2>/dev/null | awk 'NR==2{print $4}' | sed 's/G//' || echo "0")
    
    if (( available_space < 2 )); then
        record_check "disk_space" "FAIL" "Low disk space: ${available_space}GB available (minimum: 2GB)" true
    elif (( available_space < 5 )); then
        record_check "disk_space" "FAIL" "Disk space warning: ${available_space}GB available (recommended: 10GB+)"
    else
        record_check "disk_space" "PASS" "Sufficient disk space: ${available_space}GB available"
    fi
}

# Check memory usage
check_memory() {
    log "DEBUG" "Checking memory usage..."
    
    local available_memory=$(free -m 2>/dev/null | awk 'NR==2{printf "%.1f", $7/1024}' || echo "0")
    
    if (( $(echo "$available_memory < 1.0" | bc -l 2>/dev/null || echo "1") )); then
        record_check "memory_usage" "FAIL" "Low available memory: ${available_memory}GB (minimum: 2GB)"
    elif (( $(echo "$available_memory < 2.0" | bc -l 2>/dev/null || echo "1") )); then
        record_check "memory_usage" "FAIL" "Memory warning: ${available_memory}GB available (recommended: 4GB+)"
    else
        record_check "memory_usage" "PASS" "Sufficient memory: ${available_memory}GB available"
    fi
}

# Check environment configuration
check_environment() {
    log "DEBUG" "Checking environment configuration..."
    
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        record_check "env_file" "FAIL" ".env file not found" true
        return
    fi
    
    # Check for required environment variables
    local required_vars=("OPENAI_API_KEY" "ANTHROPIC_API_KEY")
    local missing_vars=()
    
    source "$PROJECT_ROOT/.env" 2>/dev/null || true
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        record_check "env_variables" "FAIL" "Missing required variables: ${missing_vars[*]}" true
    else
        record_check "env_variables" "PASS" "All required environment variables are set"
    fi
}

# Check log files
check_logs() {
    log "DEBUG" "Checking log files for errors..."
    
    local log_dirs=("$PROJECT_ROOT/logs" "/opt/qaai/logs")
    local error_count=0
    
    for log_dir in "${log_dirs[@]}"; do
        if [[ -d "$log_dir" ]]; then
            # Count recent errors in log files
            local recent_errors=$(find "$log_dir" -name "*.log" -mtime -1 -exec grep -i "error\|exception\|critical" {} \; 2>/dev/null | wc -l || echo "0")
            error_count=$((error_count + recent_errors))
        fi
    done
    
    if (( error_count > 10 )); then
        record_check "log_errors" "FAIL" "High error count in logs: $error_count errors in last 24h"
    elif (( error_count > 0 )); then
        record_check "log_errors" "FAIL" "Some errors found in logs: $error_count errors in last 24h"
    else
        record_check "log_errors" "PASS" "No recent errors in log files"
    fi
}

# Output results in JSON format
output_json() {
    local timestamp=$(date -Iseconds)
    local status="healthy"
    
    if (( CRITICAL_FAILURES > 0 )); then
        status="critical"
    elif (( FAILED_CHECKS > 0 )); then
        status="warning"
    fi
    
    cat << EOF
{
  "timestamp": "$timestamp",
  "status": "$status",
  "summary": {
    "total_checks": $TOTAL_CHECKS,
    "passed": $PASSED_CHECKS,
    "failed": $FAILED_CHECKS,
    "critical_failures": $CRITICAL_FAILURES
  },
  "checks": {
EOF

    local first=true
    for check in "${!CHECK_RESULTS[@]}"; do
        if [[ "$first" == true ]]; then
            first=false
        else
            echo ","
        fi
        
        echo -n "    \"$check\": {"
        echo -n "\"status\": \"${CHECK_RESULTS[$check]}\", "
        echo -n "\"message\": \"${CHECK_MESSAGES[$check]}\""
        echo -n "}"
    done
    
    cat << EOF

  }
}
EOF
}

# Output summary
output_summary() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        output_json
        return
    fi
    
    echo
    log "INFO" "Health Check Summary:"
    log "INFO" "  Total checks: $TOTAL_CHECKS"
    log "INFO" "  Passed: $PASSED_CHECKS"
    log "INFO" "  Failed: $FAILED_CHECKS"
    log "INFO" "  Critical failures: $CRITICAL_FAILURES"
    echo
    
    if (( CRITICAL_FAILURES > 0 )); then
        log "ERROR" "System has critical failures - immediate attention required"
        return 2
    elif (( FAILED_CHECKS > 0 )); then
        log "WARN" "System has warnings but is functional"
        return 1
    else
        log "INFO" "All health checks passed - system is healthy"
        return 0
    fi
}

# Main execution
main() {
    parse_args "$@"
    
    if [[ "$JSON_OUTPUT" == false ]]; then
        log "INFO" "Starting QaAI system health check..."
        echo
    fi
    
    # Run all health checks
    check_docker
    check_docker_compose
    check_containers
    check_container_health
    check_api_endpoint
    check_web_frontend
    check_database
    check_redis
    check_disk_space
    check_memory
    check_environment
    check_logs
    
    # Output results and exit with appropriate code
    output_summary
}

# Handle script interruption
trap 'log "ERROR" "Health check interrupted"; exit 1' INT TERM

# Run main function with all arguments
main "$@"