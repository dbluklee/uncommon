#!/bin/bash

# UNCOMMON RAG 시스템 환경변수 로딩 스크립트
# 사용법: source load-env.sh

echo "🔧 UNCOMMON RAG 시스템 환경변수 로딩 중..."

# .env.global 파일 경로 찾기 (현재 디렉토리 또는 부모 디렉토리)
ENV_FILE=""
if [ -f ".env.global" ]; then
    ENV_FILE=".env.global"
elif [ -f "../.env.global" ]; then
    ENV_FILE="../.env.global"
else
    echo "❌ .env.global 파일을 찾을 수 없습니다!"
    return 1 2>/dev/null || exit 1
fi

# 환경변수 로딩 함수 정의
load_uncommon_env() {
    export NETWORK_NAME=uncommon_rag-network
    export POSTGRES_HOST=uncommon_rag-postgres
    export POSTGRES_PORT=5434
    export POSTGRES_DB=ragdb
    export POSTGRES_USER=raguser
    export POSTGRES_PASSWORD=ragpass2024!
    export MILVUS_HOST=uncommon_rag-milvus
    export MILVUS_PORT=19532
    export MILVUS_METRICS_PORT=9093
    export OLLAMA_HOST=112.148.37.41
    export OLLAMA_PORT=1884
    export OLLAMA_MODEL=gemma3
    export EMBEDDING_MODEL=BAAI/bge-m3
    export USE_CUDA=false
    export CUDA_DEVICE=0
    export SCRAPER_PORT=8011
    export INDEXING_PORT=8012
    export RAG_API_PORT=8013
    export WEBAPP_PORT=3001
    export ADMIN_API_KEY=admin_secret_key_2024
}

# 함수 실행
load_uncommon_env

echo "✅ 환경변수 로딩 완료!"
echo ""
echo "📋 주요 환경변수:"
echo "  - NETWORK_NAME: $NETWORK_NAME"
echo "  - POSTGRES_HOST: $POSTGRES_HOST ($POSTGRES_PORT)"
echo "  - MILVUS_HOST: $MILVUS_HOST ($MILVUS_PORT)"
echo "  - USE_CUDA: $USE_CUDA"
echo "  - SCRAPER_PORT: $SCRAPER_PORT"
echo "  - INDEXING_PORT: $INDEXING_PORT"
echo ""
echo "💡 Docker 명령어 실행 시 다음과 같이 사용하세요:"
echo "   load_uncommon_env && docker compose up -d"
echo ""