#!/bin/bash

# Simple script to test RETINASolver integration
# Usage: ./run_retina_tests.sh

set -e

echo "🚀 Starting RETINASolver Integration Tests..."
echo "============================================="

# Check if containers are running
echo "📋 Checking container status..."
if ! docker compose ps | grep -q "3lips-event.*Up"; then
    echo "⚠️  3lips-event container not running. Starting containers..."
    docker compose up -d --build
    echo "⏳ Waiting for containers to start..."
    sleep 5
fi

echo "✅ Containers are running"

# Copy test script to container
echo "📄 Copying test script to container..."
docker cp test_retina_solver.py 3lips-event:/app/

# Run the test
echo "🧪 Running RETINASolver integration tests..."
echo "============================================="
docker exec 3lips-event python /app/test_retina_solver.py

echo ""
echo "✅ Test execution completed!"
echo ""
echo "💡 To run additional tests manually:"
echo "   docker exec 3lips-event python /app/test_retina_solver.py"
echo ""
echo "🔧 To check container logs:"
echo "   docker compose logs -f event"
echo ""
echo "🛑 To stop containers:"
echo "   docker compose down"