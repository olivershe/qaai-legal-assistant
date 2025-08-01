#!/bin/bash
# QaAI Docker Deployment Test Script
# Tests Docker deployment in a safe environment

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "QaAI Docker Deployment Test"
echo "=========================="

# Check Docker availability
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

# Validate configurations
echo "\nValidating Docker configurations..."
docker-compose config --quiet
if [ $? -eq 0 ]; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration has errors"
    exit 1
fi

# Test build (without running)
echo "\nTesting Docker builds..."
docker-compose build --no-cache qaai-api
if [ $? -eq 0 ]; then
    echo "✅ API Docker build successful"
else
    echo "❌ API Docker build failed"
    exit 1
fi

docker-compose build --no-cache qaai-web
if [ $? -eq 0 ]; then
    echo "✅ Web Docker build successful"
else
    echo "❌ Web Docker build failed"
    exit 1
fi

# Test basic services startup
echo "\nTesting service startup..."
docker-compose up -d redis
sleep 5

# Check if Redis is running
if docker-compose ps redis | grep -q "Up"; then
    echo "✅ Redis service started successfully"
    docker-compose down
else
    echo "❌ Redis service failed to start"
    docker-compose down
    exit 1
fi

echo "\n✅ All Docker deployment tests passed!"
echo "Ready for full deployment testing"
