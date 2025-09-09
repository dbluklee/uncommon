# 🎯 RAG LLM 시스템 MVP 완성 문서

## 📋 시스템 아키텍처 (실제 구현)
```
[MVP 단순화된 구조]
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  Scraper    │────▶│ PostgreSQLDB │◀────│  Indexing   │────▶│  MilvusDB   │
│  Service    │     │   (원본DB)   │     │  Service    │     │  (VectorDB) │
│ (인증제거)  │     │  제품중심DB  │     │ (BGE-M3)    │     │ (COSINE)    │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
                                                                     ▲
┌──────────────┐                                             ┌─────────────┐
│  Web App     │────────────────────────────────────────────▶│  RAG API    │
│(모바일최적화)│◀────────────────────────────────────────────│  Service    │
│ +관리대시보드│                                             │ (스트리밍)  │
└──────────────┘                                             └─────────────┘
                                                                    │
                                                             ┌─────────────┐
                                                             │   Ollama    │
                                                             │(Gemma3-27B) │
                                                             │(외부서버)   │
                                                             └─────────────┘
```

## 🗂️ 실제 프로젝트 구조
```
uncommon/
├── CLAUDE.md            # 프로젝트 문서 (이 문서)
├── .env.global          # 전역 환경변수 (70개 변수)
├── start.sh             # 통합 시스템 시작 스크립트 ✅
├── stop.sh              # 통합 시스템 종료 스크립트 ✅
├── PostgreSQLDB/        # PostgreSQL 16 데이터베이스 ✅
│   ├── docker-compose.yml
│   ├── init.sql         # 제품 중심 스키마
│   └── .env
├── MilvusDB/           # Milvus 2.3.3 벡터DB ✅
│   ├── docker-compose.yml
│   └── .env
├── scraper/            # 스크래핑 서비스 ✅
│   ├── main.py         # FastAPI (인증 제거됨)
│   ├── scraper.py      # UNCOMMON 전용 스크래퍼
│   ├── models.py       # Product, ProductImage, ScrapingJob
│   ├── database.py
│   └── requirements.txt
├── indexing/           # 인덱싱 서비스 ✅
│   ├── main.py         # 제품 데이터 벡터화
│   ├── embedding_generator.py  # BGE-M3 (CPU/GPU)
│   ├── text_chunker.py # 제품 특화 청킹
│   ├── milvus_client.py # 벡터 스토어
│   └── requirements.txt
├── rag-api/           # RAG API 서비스 ✅
│   ├── main.py        # 질의응답 + 검색 (JWT 제거됨)
│   ├── embedding_generator.py
│   ├── vector_search.py # 벡터 검색 엔진
│   ├── llm_client.py  # Ollama 연동
│   └── requirements.txt
└── webapp/            # 웹 앱 ✅
    ├── index.html     # 모바일 최적화 채팅 UI
    ├── admin.html     # 관리자 대시보드
    ├── debug.html     # 디버깅 페이지
    └── docker-compose.yml
```

## 🌍 환경변수 구성 (.env.global)
```bash
# 네트워크 & 서비스
NETWORK_NAME=uncommon_rag-network

# PostgreSQL 데이터베이스
POSTGRES_HOST=uncommon_rag-postgres
POSTGRES_PORT=5434          # 외부 접근 포트
POSTGRES_INTERNAL_PORT=5432 # 컨테이너 내부 포트
POSTGRES_DB=ragdb
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpass2024!

# Milvus 벡터 데이터베이스
MILVUS_HOST=uncommon_rag-milvus
MILVUS_PORT=19532
MILVUS_INTERNAL_PORT=19530
MILVUS_METRICS_PORT=9093

# Ollama LLM (외부 서버)
OLLAMA_HOST=112.148.37.41
OLLAMA_PORT=1884
OLLAMA_MODEL=gemma3:27b-it-q4_K_M

# 임베딩 모델
EMBEDDING_MODEL=BAAI/bge-m3

# CUDA 지원 (기본 활성화)
USE_CUDA=true
CUDA_DEVICE=0
CUDA_VERSION=cu121
CUDA_VISIBLE_DEVICES=0

# 서비스 포트
SCRAPER_PORT=8001
INDEXING_PORT=8002
RAG_API_PORT=8003
WEBAPP_PORT=3000

# 내부 포트
SCRAPER_INTERNAL_PORT=8000
INDEXING_INTERNAL_PORT=8000
RAG_API_INTERNAL_PORT=8000
WEBAPP_INTERNAL_PORT=80

# 기타 설정
TARGET_URL=https://ucmeyewear.earth/category/all/87/
COLLECTION_NAME=uncommon_products
DIMENSION=1024
METRIC_TYPE=COSINE
MAX_CONTEXT_LENGTH=4000
```

## 🗄️ PostgreSQL 스키마 (제품 중심)
```sql
-- 제품 중심의 실제 스키마
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    source_global_url TEXT,         -- 영문 사이트 URL
    source_kr_url TEXT,             -- 한글 사이트 URL  
    product_name TEXT NOT NULL,     -- 제품명
    color TEXT,                     -- 색상
    price JSONB DEFAULT '{}',       -- {"global": "", "kr": ""}
    reward_points JSONB DEFAULT '{}', -- 리워드 포인트
    description JSONB DEFAULT '{}', -- 제품 설명
    material JSONB DEFAULT '{}',    -- 재질
    size JSONB DEFAULT '{}',        -- 사이즈
    issoldout BOOLEAN DEFAULT FALSE, -- 품절 여부
    indexed BOOLEAN DEFAULT FALSE,   -- 벡터DB 인덱싱 상태
    scraped_at TIMESTAMP DEFAULT NOW(),
    indexed_at TIMESTAMP
);

CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    image_data BYTEA NOT NULL,      -- 이미지 바이너리 저장
    image_order INTEGER DEFAULT 0  -- 이미지 순서
);

CREATE TABLE scraping_jobs (
    id SERIAL PRIMARY KEY,
    target_url TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    products_count INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

## 🔑 실제 구현된 기술 스택

### Backend Framework
- **FastAPI 0.104.1** - 모든 API 서비스 (인증 시스템 제거됨)
- **Uvicorn** - ASGI 서버
- **SQLAlchemy 2.0.23** - PostgreSQL ORM

### AI & ML Models
- **BGE-M3** (`BAAI/bge-m3`) - 임베딩 모델 (CPU/GPU 자동 선택)
- **Ollama Gemma3** (`gemma3:27b-it-q4_K_M`) - LLM (외부 서버)
- **Sentence Transformers** - 문장 임베딩 처리

### 데이터베이스
- **PostgreSQL 16** - 제품 데이터 저장 
- **Milvus 2.3.3** - 벡터 데이터베이스 (COSINE 유사도, 1024차원)

### 웹 & UI
- **Nginx** - 정적 파일 서빙
- **Vanilla JavaScript** - 실시간 채팅 UI (모바일 최적화)
- **Server-Sent Events** - 스트리밍 응답

## 🔌 실제 구현된 API 엔드포인트

### 1. Scraper Service (포트: 8001) ✅
```
GET  /health          - 헬스체크
POST /scrape         - 스크래핑 시작 (인증 제거됨)
GET  /docs           - Swagger UI
```

### 2. Indexing Service (포트: 8002) ✅
```
GET  /               - 서비스 상태
GET  /health         - 헬스체크  
POST /index/products - 제품 벡터 인덱싱 (백그라운드)
GET  /index/stats    - 인덱싱 통계
POST /index/products/{id} - 개별 제품 인덱싱
DELETE /index/products/{id} - 인덱스에서 제품 제거
```

### 3. RAG API Service (포트: 8003) ✅
```
GET  /               - 서비스 상태
GET  /health         - 헬스체크
POST /search         - 벡터 검색 (LLM 없이)
POST /chat           - RAG 질의응답 (스트리밍 지원)
POST /chat/multimodal - 멀티모달 채팅 (이미지 업로드)
GET  /stats          - 시스템 통계
```

### 4. Web App (포트: 3000) ✅
```
/                    - 메인 채팅 인터페이스
/admin.html          - 관리자 대시보드
/debug.html          - 디버깅 페이지
```

## 🚀 시스템 시작 명령 (간소화됨)

### 전체 시스템 시작
```bash
./start.sh  # 모든 서비스를 순차적으로 시작하고 상태 확인
```

### 전체 시스템 종료
```bash  
./stop.sh   # 모든 Docker 컨테이너 정리
```

### 개별 서비스 시작
```bash
cd [service_name] 
source ../.env.global  # 환경변수 로딩 필수
docker compose up -d
```

## 📌 중요한 변경사항 (MVP 간소화)

### 🚫 제거된 기능들
1. **인증 시스템 완전 제거**
   - JWT 토큰 인증 로직 제거
   - ADMIN_API_KEY 인증 제거
   - admin-login.html 파일 삭제
   - 모든 API가 공개 접근

2. **환경변수 엄격화**
   - 모든 `os.getenv()` → `os.environ[]` 변환
   - Docker Compose 기본값 제거 (${VAR:-default} 금지)
   - 누락된 환경변수 시 명확한 에러 발생

3. **Docker 구성 개선**
   - 모든 `version: '3.8'` 제거 (obsolete 경고 해결)
   - CUDA를 기본값으로 설정 (`USE_CUDA=true`)
   - 네트워크 이름 통일 (`uncommon_rag-network`)

### ✅ 추가된 기능들
1. **멀티모달 지원**
   - 이미지 업로드 기능 (`/chat/multimodal`)
   - 제품 이미지 바이너리 저장 (PostgreSQL BYTEA)

2. **개선된 UI**
   - 실시간 스트리밍 채팅
   - 모바일 최적화 반응형 디자인
   - 디버깅 패널 (검색 결과 확인)

## 📊 시스템 성능 & 검증 완료

### ✅ 검증된 핵심 파이프라인
- **스크래핑**: UNCOMMON 사이트에서 2개 제품, 20개 이미지 성공 ✅
- **데이터 저장**: PostgreSQL에 JSON 구조로 제품 데이터 저장 ✅
- **벡터 인덱싱**: BGE-M3 모델로 1024차원 임베딩, Milvus 저장 ✅
- **RAG 검색**: 코사인 유사도 기반 상위 5개 결과 반환 ✅
- **LLM 응답**: Ollama Gemma3으로 자연어 답변 생성 (스트리밍) ✅
- **웹 UI**: 모바일 최적화 실시간 채팅 인터페이스 ✅

### 🔗 서비스 접속 정보
- **사용자 채팅**: `http://localhost:3000`
- **관리자 대시보드**: `http://localhost:3000/admin.html`
- **RAG API**: `http://localhost:8003/docs`
- **Scraper API**: `http://localhost:8001/docs`
- **Indexing API**: `http://localhost:8002/docs`

---

## 🎯 계획되었으나 미구현된 기능들

### 1. QR 코드 생성 📱
- **계획**: 모바일 접속용 QR 코드 자동 생성
- **상태**: 미구현 (추후 확장 가능)

### 2. 음성 인식 🎤
- **계획**: 음성으로 질문하기
- **상태**: 미구현 (Web Speech API 활용 가능)

### 3. 고급 보안 기능 🔒
- **계획**: OAuth 2.0, HTTPS, Rate Limiting
- **상태**: 미구현 (현재 모든 API 공개 접근)

### 4. 성능 모니터링 📈
- **계획**: Grafana + Prometheus 대시보드
- **상태**: 미구현 (기본 헬스체크만 제공)

### 5. 캐싱 시스템 ⚡
- **계획**: Redis 기반 응답 캐싱
- **상태**: 미구현 (매번 벡터 검색 수행)

### 6. 자동 스케일링 ☁️
- **계획**: Kubernetes 기반 자동 확장
- **상태**: 미구현 (Docker Compose만 지원)

---

## 🎉 MVP 완성 상태

### ✅ 완전히 작동하는 핵심 기능
- **전체 데이터 파이프라인**: 스크래핑 → 저장 → 벡터화 → 검색 → LLM 응답 ✅
- **모바일 웹 인터페이스**: 실시간 스트리밍 채팅 UI ✅  
- **멀티모달 지원**: 텍스트 + 이미지 업로드 ✅
- **CUDA GPU 가속**: BGE-M3 임베딩 모델 가속화 ✅
- **운영 도구**: 통합 start/stop 스크립트, 디버깅 패널 ✅

### 🚀 운영 준비 완료
- **Docker 컨테이너화**: 모든 서비스가 컨테이너로 실행 ✅
- **환경변수 관리**: .env.global 중앙 집중식 관리 ✅
- **에러 처리**: 누락된 환경변수 시 명확한 에러 메시지 ✅
- **헬스체크**: 모든 서비스에 헬스체크 엔드포인트 ✅

---

## 🔧 일반 사용 가이드

### 📋 사용 시나리오
1. **제품 데이터 수집**: `POST /scrape` API로 UNCOMMON 사이트 스크래핑
2. **자동 벡터화**: 백그라운드에서 제품 데이터 임베딩 및 Milvus 저장
3. **사용자 질의**: 웹 채팅에서 제품 관련 질문 입력
4. **실시간 응답**: RAG 기반 정확한 답변을 스트리밍으로 제공

### 🛠️ 관리 작업
- **시스템 모니터링**: `GET /stats` API로 각 서비스 상태 확인
- **디버깅**: 웹 UI의 디버깅 패널로 검색 결과 및 프롬프트 분석
- **수동 인덱싱**: `POST /index/products/{id}` API로 개별 제품 재인덱싱

### ⚠️ 현재 한계사항
- **보안**: 모든 API가 인증 없이 공개 접근 (MVP 간소화)
- **확장성**: 단일 서버 구성, 자동 스케일링 미지원
- **캐싱**: 응답 캐싱 없음, 매번 실시간 검색 수행
- **의존성**: 외부 Ollama 서버에 의존적

---

이 문서는 실제 구현된 MVP 시스템의 현재 상태를 정확히 반영하며, 계획 단계에서 변경된 모든 사항들을 포함하고 있습니다.