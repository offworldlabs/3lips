#!/bin/bash

# verify-retina-services.sh
# Verify all RETINA services are running for integration tests

set -e

echo "🔍 Verifying RETINA services..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a service is responding
check_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "Checking $name... "
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC}"
            return 0
        fi
        attempt=$((attempt+1))
        sleep 1
    done
    
    echo -e "${RED}✗${NC}"
    return 1
}

# Track overall status
all_good=true

# Check synthetic ADS-B service
if ! check_service "Synthetic ADS-B" "http://localhost:5001/data/aircraft.json"; then
    all_good=false
fi

# Check ADSB2DD service
if ! check_service "ADSB2DD" "http://localhost:49155/api/status"; then
    all_good=false
fi

# Check radar services
if ! check_service "Radar 1" "http://localhost:49158/api/config"; then
    all_good=false
fi

if ! check_service "Radar 2" "http://localhost:49159/api/config"; then
    all_good=false
fi

if ! check_service "Radar 3" "http://localhost:49160/api/config"; then
    all_good=false
fi

# Check 3lips API
if ! check_service "3lips API" "http://localhost:8080"; then
    all_good=false
fi

# Check 3lips Cesium
if ! check_service "3lips Cesium" "http://localhost:8081"; then
    all_good=false
fi

echo ""

if [ "$all_good" = true ]; then
    echo -e "${GREEN}✅ All RETINA services are running!${NC}"
    echo ""
    echo "You can now run the RETINASolver integration tests with Puppeteer MCP."
    echo ""
    echo "Available test suites:"
    echo "  - tests/integration/tests/mvp-retina-solver.test.js (UI tests)"
    echo "  - tests/integration/tests/retina-solver-pipeline.test.js (Pipeline tests)"
    echo "  - tests/integration/tests/e2e-retina-solver.test.js (End-to-end tests)"
    exit 0
else
    echo -e "${RED}❌ Some services are not running!${NC}"
    echo ""
    echo "Please ensure all services are started with:"
    echo "  docker compose -f tests/docker-compose.retina.yml up -d"
    echo ""
    echo "Check logs with:"
    echo "  docker compose -f tests/docker-compose.retina.yml logs"
    exit 1
fi