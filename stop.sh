#!/bin/bash

# RAG LLM System Stop Script

echo "🛑 Stopping RAG LLM System..."

# Load environment variables (required)
if [ -f ".env.global" ]; then
    export $(grep -v '^#' .env.global | xargs)
    echo "   - Environment variables loaded from .env.global"
else
    echo "   - ERROR: .env.global not found!"
    exit 1
fi

# Stop all services in reverse order (applications first, then databases)
echo "🔧 Stopping application services..."
cd scraper && docker compose down 2>/dev/null || echo "Scraper service not running"
cd ../indexing && docker compose down 2>/dev/null || echo "Indexing service not running"
cd ../rag-api && docker compose down 2>/dev/null || echo "RAG API service not running"  
cd ../webapp && docker compose down 2>/dev/null || echo "Web app service not running"

# Stop databases
echo "🗄️ Stopping databases..."
cd ../PostgreSQLDB && docker compose down 2>/dev/null || echo "PostgreSQL not running"
cd ../MilvusDB && docker compose down 2>/dev/null || echo "Milvus not running"

# Return to project root
cd ..

# Clean up Docker resources
echo "🧹 Cleaning up Docker resources..."

# Remove any stopped containers with uncommon prefix
echo "   - Removing stopped containers..."
docker container prune -f --filter "label=com.docker.compose.project=uncommon*" 2>/dev/null || true

# Remove unused images related to the project
echo "   - Removing unused images..."
docker image prune -f --filter "label=com.docker.compose.project=uncommon*" 2>/dev/null || true

# Clean up the custom network if it exists and is not being used
echo "   - Cleaning up network..."
docker network rm "$NETWORK_NAME" 2>/dev/null || echo "   - Network $NETWORK_NAME still in use or doesn't exist"

# Kill any background bash processes that might be running start.sh
echo "🔄 Stopping any background processes..."
pkill -f "start.sh" 2>/dev/null || echo "   - No background start.sh processes found"

echo "✅ All services and resources cleaned up successfully!"