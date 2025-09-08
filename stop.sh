#!/bin/bash

# RAG LLM System Stop Script

echo "🛑 Stopping RAG LLM System..."

# Load environment variables
if [ -f ".env.global" ]; then
    export $(grep -v '^#' .env.global | xargs)
fi

# Stop all services
echo "🔧 Stopping application services..."
cd scraper && docker compose down
cd ../indexing && docker compose down 2>/dev/null || echo "Indexing service not running"
cd ../rag-api && docker compose down 2>/dev/null || echo "RAG API service not running"  
cd ../webapp && docker compose down 2>/dev/null || echo "Web app service not running"

# Stop databases
echo "🗄️ Stopping databases..."
cd ../PostgreSQLDB && docker compose down
cd ../MilvusDB && docker compose down

echo "✅ All services stopped!"