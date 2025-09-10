#!/bin/bash

# RAG LLM 시스템 통합 시작 스크립트 - 전체 마이크로서비스 생명주기 관리
# 목적: PostgreSQL, Milvus, Scraper, Indexing, RAG API, WebApp 순차 시작 및 상태 확인
# 주요 기능: 네트워크 생성, 의존성 순서 제어, 헬스체크, 자동 IP 감지
# 한 번의 명령으로 모든 서비스를 완전히 작동 가능한 상태로 구성

set -e  # Bash 엄격 모드 - 어떤 명령이라도 실패하면 스크립트 전체 중단

echo "🚀 UNCOMMON RAG LLM 시스템 시작..."
echo "=================================================="
echo ""

# 스크립트 UI 헬퍼 함수 - 실행 진행 상황을 명확하게 시각적 구분
# 목적: 각 실행 단계를 사용자에게 명확하게 알리는 일관성 있는 UI 제공
display_header() {
    echo ""
    echo "📋 $1"
    echo "=================================================="  # 50자 등호 선
}

# 진행 상황 표시 함수 - 사용자에게 대기 시간 시각적 피드백 제공
# 목적: 긴 대기 시간 동안 사용자가 진행 상황을 시각적으로 확인할 수 있도록 도트 애니메이션
wait_with_progress() {
    local seconds=$1  # 대기 시간(초)
    local message=$2  # 표시할 메시지
    echo -n "$message"
    for i in $(seq 1 $seconds); do
        echo -n "."  # 매초마다 도트 추가
        sleep 1
    done
    echo " ✅"  # 완료 표시
}

# 서비스 준비도 검사 함수 - HTTP 엔드포인트를 통한 서비스 상태 확인
# 목적: Docker 컨테이너 시작과 실제 서비스 준비 완료를 구분하여 안정적인 시스템 구동 보장
# 방식: /health 또는 / 엔드포인트에 HTTP 요청을 주기적으로 전송하여 응답 확인
check_service_health() {
    local service_name=$1  # 서비스 이름 (표시용)
    local port=$2  # HTTP 포트 번호
    local max_attempts=${3:-30}  # 최대 시도 횟수 (기본 30회)
    
    echo "🔍 $service_name 상태 확인 중..."
    for i in $(seq 1 $max_attempts); do
        # /health 또는 / 엔드포인트에 HTTP 요청 전송 (-s: silent, -f: fail on error)
        if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1 || curl -s -f "http://localhost:$port/" > /dev/null 2>&1; then
            echo "✅ $service_name 준비 완료"  # 정상 응답 수신
            return 0  # 성공 반환
        fi
        echo "⏳ $service_name 시작 대기 중... ($i/$max_attempts)"
        sleep 2  # 2초 대기 후 재시도
    done
    echo "❌ $service_name 시작 실패"  # 최대 시도 횟수 초과
    return 1  # 실패 반환
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
            # Milvus는 Docker 컨테이너 상태로 확인
            if docker ps --filter "name=${container_name}" --filter "health=healthy" | grep -q "${container_name}"; then
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
    # .env.global 파일에서 환경변수를 로드하고 export
    set -a  # 모든 변수를 자동으로 export
    source .env.global
    set +a  # export 자동화 해제
    echo "✅ 환경변수 로딩 완료"
    echo "   - 네트워크: ${NETWORK_NAME}"
    echo "   - 서비스 포트: Scraper(${SCRAPER_PORT}), Indexing(${INDEXING_PORT}), RAG-API(${RAG_API_PORT}), WebApp(${WEBAPP_PORT})"
else
    echo "❌ .env.global 파일을 찾을 수 없습니다!"
    exit 1
fi

echo "📡 Docker 네트워크 생성..."
docker network create ${NETWORK_NAME} 2>/dev/null && echo "✅ 네트워크 생성 완료" || echo "✅ 네트워크 이미 존재"

# STEP 2: Database Services (순차 실행)
display_header "2. 데이터베이스 서비스 시작"

echo "🗄️ PostgreSQL 데이터베이스 시작..."
cd PostgreSQLDB
docker compose up -d --build
cd ..

echo "⏳ PostgreSQL 준비 완료 대기..."
check_database "PostgreSQL" "${POSTGRES_HOST}"

echo "📊 Milvus 벡터 데이터베이스 시작..."
cd MilvusDB
docker compose up -d --build
cd ..

echo "⏳ Milvus 준비 완료 대기..."
check_database "Milvus" "${MILVUS_HOST}"

echo "✅ 모든 데이터베이스 준비 완료"

# STEP 3: Router LLM Service (먼저 시작)
display_header "3. Router LLM 서비스 시작"

echo "🎯 Router LLM (Ollama) 시작..."
cd RouterOllama
docker compose up -d --build
cd ..

echo "⏳ Router LLM 준비 완료 대기..."
check_service_health "Router LLM" "${ROUTER_OLLAMA_PORT}"

echo "✅ Router LLM 준비 완료"

# STEP 4: Application Services (의존성 순서로 순차 실행)
display_header "4. 애플리케이션 서비스 시작"

echo "🔍 Scraper 서비스 시작..."
cd scraper
docker compose up -d --build
cd ..

echo "⏳ Scraper 서비스 준비 완료 대기..."
check_service_health "Scraper API" "${SCRAPER_PORT}"

echo "🧠 Indexing 서비스 시작..."
cd indexing
docker compose up -d --build
cd ..

echo "⏳ Indexing 서비스 준비 완료 대기... (모델 로딩으로 인해 시간이 오래 걸립니다)"
check_service_health "Indexing API" "${INDEXING_PORT}" 150

echo "🤖 RAG API 서비스 시작..."
cd rag-api
docker compose up -d --build
cd ..

echo "⏳ RAG API 서비스 준비 완료 대기... (모델 로딩으로 인해 시간이 오래 걸립니다)"
check_service_health "RAG API" "${RAG_API_PORT}" 150

echo "🌐 웹 애플리케이션 시작..."
cd webapp
docker compose up -d --build
cd ..

echo "⏳ 웹 애플리케이션 준비 완료 대기..."
check_service_health "Web App" "${WEBAPP_PORT}"

echo "✅ 모든 애플리케이션 서비스 준비 완료"

# STEP 5: Final Health Check Summary
display_header "5. 최종 서비스 상태 확인"

echo "🔍 모든 서비스 최종 상태 확인..."
echo ""

# Final check (should all be ready now)
services_ready=true

echo "🎯 Router LLM 최종 확인..."
if curl -s -f "http://localhost:${ROUTER_OLLAMA_PORT}/api/tags" > /dev/null 2>&1; then
    echo "✅ Router LLM 정상 작동"
else
    echo "❌ Router LLM 문제 발생"
    services_ready=false
fi

echo "📊 Scraper API 최종 확인..."
if curl -s -f "http://localhost:${SCRAPER_PORT}/health" > /dev/null 2>&1 || curl -s -f "http://localhost:${SCRAPER_PORT}/" > /dev/null 2>&1; then
    echo "✅ Scraper API 정상 작동"
else
    echo "❌ Scraper API 문제 발생"
    services_ready=false
fi

echo "🧠 Indexing API 최종 확인..."  
if curl -s -f "http://localhost:${INDEXING_PORT}/health" > /dev/null 2>&1 || curl -s -f "http://localhost:${INDEXING_PORT}/" > /dev/null 2>&1; then
    echo "✅ Indexing API 정상 작동"
else
    echo "❌ Indexing API 문제 발생"
    services_ready=false
fi

echo "🤖 RAG API 최종 확인..."
if curl -s -f "http://localhost:${RAG_API_PORT}/health" > /dev/null 2>&1 || curl -s -f "http://localhost:${RAG_API_PORT}/" > /dev/null 2>&1; then
    echo "✅ RAG API 정상 작동"
else
    echo "❌ RAG API 문제 발생"  
    services_ready=false
fi

echo "🌐 Web App 최종 확인..."
if curl -s -f "http://localhost:${WEBAPP_PORT}/" > /dev/null 2>&1; then
    echo "✅ 웹 애플리케이션 정상 작동"
else
    echo "❌ 웹 애플리케이션 문제 발생"
    services_ready=false
fi

echo ""

# STEP 6: Final Status
display_header "6. 시작 완료"

# 외부 공인 IP 주소 자동 감지
EXTERNAL_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "localhost")
if [ "$EXTERNAL_IP" = "localhost" ]; then
    echo "⚠️ 공인 IP 주소를 가져올 수 없어 localhost를 사용합니다"
    EXTERNAL_IP="localhost"
else
    echo "🌐 감지된 공인 IP 주소: $EXTERNAL_IP"
fi

echo ""
if [ "$services_ready" = true ]; then
    echo "🎉 모든 서비스가 성공적으로 시작되었습니다!"
    echo ""
    echo "💬 **지금 채팅을 시작하세요:**"
    echo "   👉 http://${EXTERNAL_IP}:${WEBAPP_PORT}"
    echo ""
    echo "🔗 **관리자 URL:**"
    echo "   📊 Admin:  http://192.168.50.40:${WEBAPP_PORT}/admin.html"
    echo ""
    echo "📚 **데이터베이스:**"
    echo "   🗄️ PostgreSQL:     ${EXTERNAL_IP}:${POSTGRES_PORT}"
    echo "   📊 Milvus:         ${EXTERNAL_IP}:${MILVUS_PORT}"
    echo ""
    echo "✨ **이미지 첨부 기능**도 포함되어 있습니다!"
    echo "📱 모바일에서도 최적화된 인터페이스를 경험하세요."
    echo ""
    echo "🕷️ **스크래핑 시작 명령어:**"
    echo "   curl -X POST \"http://localhost:${SCRAPER_PORT}/scrape\" \\"
    echo "     -H \"Content-Type: application/json\" \\"
    echo "     -d '{\"target_url\": \"https://ucmeyewear.earth/category/all/87/\", \"force_rescrape\": false}'"
    echo ""
else
    echo "❌ 일부 서비스에 문제가 발생했습니다."
    echo "💡 로그를 확인하여 문제를 해결하세요: docker logs [컨테이너명]"
    echo ""
    echo "📝 **접속 URL (문제가 해결되면):**"
    echo "   💬 채팅:           http://${EXTERNAL_IP}:${WEBAPP_PORT}"
    echo "   🤖 RAG API:        http://${EXTERNAL_IP}:${RAG_API_PORT}"
    echo ""
fi

echo "🛑 **시스템 종료:** ./stop.sh"
echo "🔍 **로그 확인:** docker logs [컨테이너명]"
echo ""
echo "=================================================="