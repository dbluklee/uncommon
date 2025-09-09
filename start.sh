#!/bin/bash

# UNCOMMON RAG LLM System - Complete Startup Script
# 한 번의 실행으로 모든 서비스를 준비하고 채팅 가능한 상태로 만듭니다

set -e  # 오류 발생 시 스크립트 중단

echo "🚀 UNCOMMON RAG LLM 시스템 시작..."
echo "=================================================="
echo ""

# Function: Display header
display_header() {
    echo ""
    echo "📋 $1"
    echo "=================================================="
}

# Function: Wait with progress indicator
wait_with_progress() {
    local seconds=$1
    local message=$2
    echo -n "$message"
    for i in $(seq 1 $seconds); do
        echo -n "."
        sleep 1
    done
    echo " ✅"
}

# Function: Check service health
check_service_health() {
    local service_name=$1
    local port=$2
    local max_attempts=${3:-30}
    
    echo "🔍 $service_name 상태 확인 중..."
    for i in $(seq 1 $max_attempts); do
        if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1 || curl -s -f "http://localhost:$port/" > /dev/null 2>&1; then
            echo "✅ $service_name 준비 완료"
            return 0
        fi
        echo "⏳ $service_name 시작 대기 중... ($i/$max_attempts)"
        sleep 2
    done
    echo "❌ $service_name 시작 실패"
    return 1
}

# Function: Check database connection
check_database() {
    local db_type=$1
    local container_name=$2
    
    echo "🔍 $db_type 연결 확인 중..."
    for i in {1..30}; do
        if [ "$db_type" = "PostgreSQL" ]; then
            if docker exec $container_name pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} > /dev/null 2>&1; then
                echo "✅ $db_type 연결 성공"
                return 0
            fi
        elif [ "$db_type" = "Milvus" ]; then
            if curl -s -f "http://localhost:${MILVUS_PORT}/health" > /dev/null 2>&1; then
                echo "✅ $db_type 연결 성공"
                return 0
            fi
        fi
        echo "⏳ $db_type 연결 대기 중... ($i/30)"
        sleep 2
    done
    echo "❌ $db_type 연결 실패"
    return 1
}

# STEP 1: Environment Setup
display_header "1. 환경 설정"

echo "📝 환경변수 로딩 중..."
if [ -f ".env.global" ]; then
    source ./load-env.sh
    echo "✅ 환경변수 로딩 완료"
else
    echo "❌ .env.global 파일을 찾을 수 없습니다!"
    exit 1
fi

echo "📡 Docker 네트워크 생성..."
docker network create ${NETWORK_NAME} 2>/dev/null && echo "✅ 네트워크 생성 완료" || echo "✅ 네트워크 이미 존재"

# STEP 2: Database Services
display_header "2. 데이터베이스 서비스 시작"

echo "🗄️ PostgreSQL 데이터베이스 시작..."
cd PostgreSQLDB
source ../load-env.sh
docker compose up -d --build
cd ..

echo "📊 Milvus 벡터 데이터베이스 시작..."
cd MilvusDB
source ../load-env.sh  
docker compose up -d --build
cd ..

wait_with_progress 20 "⏳ 데이터베이스 초기화 대기"

# Check databases
check_database "PostgreSQL" "${POSTGRES_HOST}"
check_database "Milvus" "${MILVUS_HOST}"

# STEP 3: Application Services
display_header "3. 애플리케이션 서비스 시작"

echo "🔍 Scraper 서비스 시작..."
cd scraper
source ../load-env.sh
docker compose up -d --build
cd ..

echo "🧠 Indexing 서비스 시작..."
cd indexing
source ../load-env.sh
docker compose up -d --build
cd ..

echo "🤖 RAG API 서비스 시작..."
cd rag-api
source ../load-env.sh
docker compose up -d --build
cd ..

echo "🌐 웹 애플리케이션 시작..."
cd webapp
source ../load-env.sh
docker compose up -d --build
cd ..

# STEP 4: Health Checks
display_header "4. 서비스 상태 확인"

wait_with_progress 30 "⏳ 모든 서비스 초기화 대기"

echo ""
echo "🔍 각 서비스 상태 확인 중..."
echo ""

# Check each service (non-blocking)
services_ready=true

echo "📊 Scraper API (포트 ${SCRAPER_PORT})..."
if curl -s -f "http://localhost:${SCRAPER_PORT}/" > /dev/null 2>&1; then
    echo "✅ Scraper 서비스 준비 완료"
else
    echo "⚠️ Scraper 서비스 확인 필요"
    services_ready=false
fi

echo "🧠 Indexing API (포트 ${INDEXING_PORT})..."
if curl -s -f "http://localhost:${INDEXING_PORT}/" > /dev/null 2>&1; then
    echo "✅ Indexing 서비스 준비 완료"
else
    echo "⚠️ Indexing 서비스 확인 필요"
    services_ready=false
fi

echo "🤖 RAG API (포트 ${RAG_API_PORT})..."
if curl -s -f "http://localhost:${RAG_API_PORT}/" > /dev/null 2>&1; then
    echo "✅ RAG API 서비스 준비 완료"
else
    echo "⚠️ RAG API 서비스 확인 필요"
    services_ready=false
fi

echo "🌐 Web App (포트 ${WEBAPP_PORT})..."
if curl -s -f "http://localhost:${WEBAPP_PORT}/" > /dev/null 2>&1; then
    echo "✅ 웹 애플리케이션 준비 완료"
else
    echo "⚠️ 웹 애플리케이션 확인 필요"
    services_ready=false
fi

# STEP 5: Final Status
display_header "5. 시작 완료"

echo ""
if [ "$services_ready" = true ]; then
    echo "🎉 모든 서비스가 성공적으로 시작되었습니다!"
    echo ""
    echo "💬 **지금 채팅을 시작하세요:**"
    echo "   👉 http://localhost:${WEBAPP_PORT}"
    echo ""
    echo "🔗 **관리자 URL:**"
    echo "   📊 Scraper Admin:  http://localhost:${SCRAPER_PORT}/docs"
    echo "   🧠 Indexing API:   http://localhost:${INDEXING_PORT}/docs"
    echo "   🤖 RAG API:        http://localhost:${RAG_API_PORT}/docs"
    echo ""
    echo "📚 **데이터베이스:**"
    echo "   🗄️ PostgreSQL:     localhost:${POSTGRES_PORT}"
    echo "   📊 Milvus:         localhost:${MILVUS_PORT}"
    echo ""
    echo "✨ **이미지 첨부 기능**도 포함되어 있습니다!"
    echo "📱 모바일에서도 최적화된 인터페이스를 경험하세요."
    echo ""
else
    echo "⚠️  일부 서비스가 아직 준비 중입니다."
    echo "💡 몇 분 후에 다시 시도하거나 docker ps로 상태를 확인하세요."
    echo ""
    echo "📝 **기본 접속 URL:**"
    echo "   💬 채팅:           http://localhost:${WEBAPP_PORT}"
    echo "   🤖 RAG API:        http://localhost:${RAG_API_PORT}"
    echo ""
fi

echo "🛑 **시스템 종료:** ./stop.sh"
echo "🔍 **로그 확인:** docker logs [컨테이너명]"
echo ""
echo "=================================================="