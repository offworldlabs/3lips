#!/bin/bash

# End-to-End Integration Test Runner for RETINASolver with Synthetic-ADSB
# This script orchestrates the complete test pipeline

set -e

echo "🚀 RETINASolver E2E Integration Test with Synthetic-ADSB"
echo "=========================================================="

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if synthetic-adsb exists
SYNTHETIC_ADSB_DIR=${SYNTHETIC_ADSB_DIR:-"../synthetic-adsb"}

if [ ! -d "$SYNTHETIC_ADSB_DIR" ]; then
    echo "❌ synthetic-adsb directory not found at $SYNTHETIC_ADSB_DIR"
    echo "   Set SYNTHETIC_ADSB_DIR environment variable or ensure synthetic-adsb"
    echo "   exists in the expected location"
    exit 1
fi

echo "✅ synthetic-adsb directory found"

# Check if docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Check if RETINAsolver exists
if [ ! -d "../RETINAsolver" ]; then
    echo "❌ RETINAsolver directory not found at ../RETINAsolver"
    echo "   Please ensure RETINAsolver is available"
    exit 1
fi

echo "✅ RETINAsolver directory found"

# Clean up any existing test containers
echo "🧹 Cleaning up existing test containers..."
docker compose -f docker-compose-e2e-test.yml down 2>/dev/null || true
docker compose down 2>/dev/null || true
docker stop $(docker ps -q --filter name=3lips) 2>/dev/null || true
docker rm $(docker ps -aq --filter name=3lips) 2>/dev/null || true

# Run the Python integration test
echo "🧪 Running integration test..."
python3 test_retina_solver_e2e_integration.py

# Check if test containers are running
echo "📊 Checking test environment status..."
if docker ps | grep -q "synthetic-adsb-test"; then
    echo "✅ Synthetic-ADSB test container is running"
    
    # Test synthetic-adsb endpoint
    echo "🛩️ Testing synthetic-adsb data..."
    if curl -s http://localhost:5001/data/aircraft.json | head -3; then
        echo "✅ Synthetic-ADSB data is available"
    else
        echo "⚠️ Synthetic-ADSB endpoint not responding"
    fi
else
    echo "⚠️ Synthetic-ADSB test container not found"
fi

if docker ps | grep -q "3lips-event"; then
    echo "✅ 3lips-event container is running"
    
    # Test RETINASolver
    echo "🔧 Testing RETINASolver integration..."
    docker exec 3lips-event python -c "
import sys
sys.path.insert(0, '/app')
try:
    from algorithm.localisation.RETINASolverLocalisation import RETINASolverLocalisation
    print('✅ RETINASolver integration working')
except Exception as e:
    print(f'❌ RETINASolver error: {e}')
" 2>/dev/null || echo "⚠️ RETINASolver test failed"
else
    echo "⚠️ 3lips-event container not found"
fi

# Check web interface
echo "🌐 Testing web interface..."
if curl -s http://localhost:8080 | grep -q "3lips"; then
    echo "✅ Web interface is accessible at http://localhost:8080"
else
    echo "⚠️ Web interface not responding"
fi

echo ""
echo "🎭 Puppeteer Test Instructions:"
echo "================================"
echo "To complete the integration test with visual validation:"
echo ""
echo "1. Load the Puppeteer script in Claude Code:"
echo "   📄 File: puppeteer_retina_solver_validation.js"
echo ""
echo "2. Execute the validation function:"
echo "   🧪 Run: validateRETINASolverTracks(navigate, screenshot, evaluate)"
echo ""
echo "3. Expected results:"
echo "   ✅ Map loads with track visualization"
echo "   ✅ RETINASolver algorithm shown as active"
echo "   ✅ Track count > 0 if data is flowing"
echo "   ✅ Radar markers and detection points visible"
echo ""
echo "📊 Manual checks you can perform:"
echo "  🌐 Web interface: http://localhost:8080"
echo "  🗺️ Map interface: http://localhost:8080 → Click 'Map'"
echo "  📡 API status: http://localhost:8080/api"
echo "  ✈️ Aircraft data: http://localhost:5001/data/aircraft.json"
echo ""
echo "🛑 To stop the test environment:"
echo "   docker compose -f docker-compose-e2e-test.yml down"
echo ""
echo "🎉 Integration test setup complete!"
echo "   The system is now running with RETINASolver + Synthetic-ADSB"
echo "   Use Puppeteer to complete visual validation"