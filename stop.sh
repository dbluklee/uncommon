#!/bin/bash

# RAG LLM System Stop Script

echo "🛑 Stopping RAG LLM System..."

# Stop all services
cd scraper && docker-compose down
cd ../indexing && docker-compose down
cd ../rag-api && docker-compose down
cd ../webapp && docker-compose down

# Stop databases
cd ../PostgreSQLDB && docker-compose down
cd ../MilvusDB && docker-compose down

echo "✅ All services stopped!"