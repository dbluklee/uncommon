#!/bin/bash

# RAG LLM System Startup Script

echo "🚀 Starting RAG LLM System..."

# 1. Create Docker network
echo "📡 Creating Docker network..."
docker network create rag-network 2>/dev/null || echo "Network already exists"

# 2. Start databases first (rebuild without cache)
echo "🗄️ Starting databases..."
cd PostgreSQLDB && docker-compose up -d --build --force-recreate
cd ../MilvusDB && docker-compose up -d --build --force-recreate

# Wait for databases to be ready
echo "⏳ Waiting for databases to start..."
sleep 15

# 3. Start application services (rebuild without cache)
echo "🔧 Starting services..."
cd ../scraper && docker-compose up -d --build --force-recreate
cd ../indexing && docker-compose up -d --build --force-recreate
cd ../rag-api && docker-compose up -d --build --force-recreate
cd ../webapp && docker-compose up -d --build --force-recreate

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