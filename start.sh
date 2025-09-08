#!/bin/bash

# RAG LLM System Startup Script

echo "🚀 Starting RAG LLM System..."

# Load and export environment variables from .env.global
echo "📝 Loading environment variables..."
if [ -f ".env.global" ]; then
    export $(grep -v '^#' .env.global | xargs)
    echo "✅ Environment variables loaded from .env.global"
else
    echo "❌ .env.global file not found!"
    exit 1
fi

# 1. Create Docker network
echo "📡 Creating Docker network..."
docker network create ${NETWORK_NAME} 2>/dev/null || echo "Network ${NETWORK_NAME} already exists"

# 2. Start databases first (rebuild without cache)
echo "🗄️ Starting databases..."
cd PostgreSQLDB && docker compose up -d --build --force-recreate
cd ../MilvusDB && docker compose up -d --build --force-recreate

# Wait for databases to be ready
echo "⏳ Waiting for databases to start..."
sleep 15

# Check if PostgreSQL is ready
echo "🔍 Checking PostgreSQL connection..."
for i in {1..30}; do
    if docker exec ${POSTGRES_HOST} pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    echo "⏳ Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# 3. Start application services (rebuild without cache)
echo "🔧 Starting services..."
cd ../scraper && docker compose up -d --build --force-recreate

echo ""
echo "✅ All services started!"
echo ""
echo "🔗 Service URLs:"
echo "   - Scraper Admin: http://localhost:8001"
echo "   - Indexing Service: http://localhost:8002"
echo "   - RAG API: http://localhost:8003"
echo "   - Web App: http://localhost:3000"
echo ""
echo "📊 Monitoring:"
echo "   - PostgreSQL: localhost:5432"
echo "   - Milvus: localhost:19530"
echo ""
echo "🛑 To stop all services, run: ./stop.sh"