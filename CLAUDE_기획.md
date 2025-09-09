# 🎯 RAG LLM 시스템 MVP 개발 계획

## 📋 시스템 아키텍처
```
[관리자 영역]
     Admin
       │
       ▼ (수동 실행)
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  Scraper    │────▶│ PostgreSQLDB │◀────│  Indexing   │────▶│  MilvusDB   │
│  Service    │     │   (원본DB)   │     │  Service    │     │  (VectorDB) │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
                                            (BGE-M3 임베딩)           ▲
[사용자 영역]                                                         │
┌─────────────┐                                              ┌─────────────┐
│  Web App    │─────────────────────────────────────────────▶│  RAG API    │
│  (QR접속)   │◀─────────────────────────────────────────────│  Service    │
└─────────────┘                                              └─────────────┘
                                                                      │
                                                              ┌─────────────┐
                                                              │   Ollama    │
                                                              │  (Gemma3)   │
                                                              └─────────────┘
```

## 🗂️ 프로젝트 구조
```
uncommon/
├── CLAUDE.md            # Claude Code 참조 문서 (이 문서)
├── .env.global          # 전역 환경변수
├── load-env.sh          # 환경변수 로딩 스크립트 ⚠️ 모든 Docker 작업 전 필수 실행
├── PostgreSQLDB/        # PostgreSQL 데이터베이스
│   ├── .env
│   ├── docker-compose.yml
│   ├── init.sql
│   └── data/
├── MilvusDB/           # Milvus 벡터 데이터베이스
│   ├── .env
│   ├── docker-compose.yml
│   └── data/
├── scraper/            # 스크래핑 서비스
│   ├── .env
│   ├── main.py
│   ├── scraper.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── indexing/           # Indexing 서비스 (BGE-M3)
│   ├── .env
│   ├── main.py
│   ├── processor.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── rag-api/           # RAG API 서비스
│   ├── .env
│   ├── main.py
│   ├── rag_engine.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── webapp/            # 웹 인터페이스
│   ├── .env
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── Dockerfile
│   └── docker-compose.yml
└── start.sh           # 전체 시스템 시작 스크립트
```

## 🌍 전역 환경변수 (.env.global)
```bash
# Network
NETWORK_NAME=rag-network

# PostgreSQL
POSTGRES_HOST=rag-postgres
POSTGRES_PORT=5432
POSTGRES_DB=ragdb
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpass2024!

# Milvus
MILVUS_HOST=rag-milvus
MILVUS_PORT=19530
MILVUS_METRICS_PORT=9091

# Ollama (Gemma3)
OLLAMA_HOST=112.148.37.41
OLLAMA_PORT=1884
OLLAMA_MODEL=gemma3

# Embedding Model
EMBEDDING_MODEL=BAAI/bge-m3

# Service Ports
SCRAPER_PORT=8001
INDEXING_PORT=8002
RAG_API_PORT=8003
WEBAPP_PORT=3000

# Admin
ADMIN_API_KEY=admin_secret_key_2024
```

## 🗄️ PostgreSQL 스키마
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    content TEXT NOT NULL,
    indexed BOOLEAN DEFAULT FALSE,
    scraped_at TIMESTAMP DEFAULT NOW(),
    indexed_at TIMESTAMP
);

CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    url TEXT NOT NULL,
    alt_text TEXT,
    context TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE scraping_logs (
    id SERIAL PRIMARY KEY,
    target_url TEXT NOT NULL,
    status VARCHAR(20),
    documents_count INTEGER DEFAULT 0,
    images_count INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_documents_indexed ON documents(indexed);
CREATE INDEX idx_documents_url ON documents(url);
```

## 🔑 핵심 기술 스택
- **임베딩**: BGE-M3 (다국어 지원, 최대 8192 토큰)
- **LLM**: Ollama Gemma3 (멀티모달 지원)
- **벡터DB**: Milvus 2.3.3
- **원본DB**: PostgreSQL 16
- **웹프레임워크**: FastAPI
- **스크래핑**: BeautifulSoup4

## 📝 개발 작업 순서
1. **인프라 설정**
   - [ ] .env.global 파일 생성
   - [ ] PostgreSQLDB Docker 구성
   - [ ] MilvusDB Docker 구성

2. **Scraper Service**
   - [ ] FastAPI 기본 구조
   - [ ] 관리자 인증 API
   - [ ] BeautifulSoup 스크래핑 로직
   - [ ] PostgreSQL 저장

3. **Indexing Service**
   - [ ] BGE-M3 모델 설정
   - [ ] 문서 청킹 로직
   - [ ] 임베딩 생성 및 Milvus 저장
   - [ ] PostgreSQL 상태 업데이트

4. **RAG API Service**
   - [ ] BGE-M3 쿼리 임베딩
   - [ ] Milvus 유사도 검색
   - [ ] Ollama/Gemma3 응답 생성
   - [ ] 스트리밍 API

5. **Web App**
   - [ ] QR 코드 생성
   - [ ] 모바일 UI
   - [ ] 이미지 업로드
   - [ ] 채팅 인터페이스

## 🔧 주요 API 엔드포인트

### Scraper (관리자용)
- `POST /admin/scrape` - 스크래핑 시작
- `GET /admin/status` - 진행 상태 확인

### Indexing (내부용)
- `POST /index/document/{id}` - 문서 인덱싱
- `GET /index/status` - 인덱싱 상태

### RAG API (사용자용)
- `POST /chat` - 질문 응답
- `POST /chat/stream` - 스트리밍 응답

### Web App
- QR 접속: `http://localhost:3000`

## 🚀 시스템 시작 명령 (검증된 방법)
```bash
# 0. 네트워크 생성 (환경변수 로딩 포함)
source load-env.sh && docker network create $NETWORK_NAME

# 1. 데이터베이스 시작 (검증됨 ✅)
cd PostgreSQLDB && source ../load-env.sh && docker compose up -d
cd ../MilvusDB && source ../load-env.sh && docker compose up -d

# 2. 서비스 시작
cd ../scraper && source ../load-env.sh && docker compose up -d
cd ../indexing && source ../load-env.sh && docker compose up -d
cd ../rag-api && source ../load-env.sh && docker compose up -d
cd ../webapp && source ../load-env.sh && docker compose up -d
```

### 🎯 개별 서비스 시작 예시
```bash
# Milvus만 시작 (검증됨 ✅)
cd MilvusDB && source ../load-env.sh && docker compose up -d

# PostgreSQL만 시작  
cd PostgreSQLDB && source ../load-env.sh && docker compose up -d

# Scraper만 시작
cd scraper && source ../load-env.sh && docker compose up -d
```

## 📌 개발 시 주의사항
1. **환경변수 필수 로딩**: 모든 Docker 작업이나 테스트 전에 반드시 환경변수를 먼저 로딩해야 함

   ### 🔥 환경변수 로딩 가이드 (성공 검증됨)
   
   **루트 디렉토리에서 실행:**
   ```bash
   source load-env.sh
   ```
   
   **서브 디렉토리에서 실행:**
   ```bash
   # MilvusDB, PostgreSQLDB, scraper, indexing 등에서 실행 시
   source ../load-env.sh && docker compose up -d
   ```
   
   **검증된 성공 사례:**
   ```bash
   # Milvus 컨테이너 시작 (성공 확인됨)
   cd MilvusDB && source ../load-env.sh && docker compose up -d
   
   # PostgreSQL 컨테이너 시작  
   cd PostgreSQLDB && source ../load-env.sh && docker compose up -d
   ```
   
   **⚠️ 중요**: Claude Code bash에서는 환경변수가 세션 간 지속되지 않으므로 매번 Docker 명령어 실행 전에 load-env.sh를 source해야 함

2. 모든 서비스는 Docker 컨테이너로 실행
3. 환경변수는 .env.global과 각 서비스별 .env 파일로 관리
4. BGE-M3 임베딩 모델은 첫 실행 시 자동 다운로드
5. Ollama는 외부 서버(112.148.37.41:1884)에서 실행 중
6. 관리자 API는 ADMIN_API_KEY로 인증
7. **환경변수 예외처리 금지**: Docker Compose 파일에서 환경변수 사용 시 기본값(${VAR:-default}) 사용 금지. 환경변수가 없으면 에러가 발생하도록 하여 설정 오류를 빠르게 파악할 수 있도록 함
8. **포트 충돌 방지**: 각 서비스별 고유 포트를 .env.global에 정의하여 다른 프로젝트와 충돌 방지

---

## 📊 현재 개발 진행 상황 (2025-09-09)

### ✅ 완료된 작업
1. **프로젝트 기본 구조**
   - CLAUDE.md 파일 생성 및 계획 문서화 ✅
   - .env.global 전역 환경변수 설정 ✅
   - 프로젝트 폴더 구조 생성 ✅

2. **PostgreSQL 데이터베이스**
   - Docker 구성 (PostgreSQLDB/docker-compose.yml) ✅
   - 스키마 정의 (init.sql) - 제품 중심 구조 ✅
   - 환경변수 설정 (.env) ✅

3. **Milvus 벡터 데이터베이스**
   - Docker 구성 (MilvusDB/docker-compose.yml) ✅
   - 환경변수 설정 (.env) ✅

4. **Scraper 서비스 ✅ 완료**
   - requirements.txt - BeautifulSoup4, psycopg2 등 패키지 ✅
   - Dockerfile - Python 3.11 컨테이너 설정 ✅
   - docker-compose.yml - 서비스 구성 ✅
   - 환경변수 설정 (.env) ✅
   - main.py - FastAPI 애플리케이션 (관리자 API) ✅
   - database.py - PostgreSQL 연결 ✅
   - models.py - SQLAlchemy 모델 (Product, ProductImage, ScrapingJob) ✅
   - scraper.py - UNCOMMON 사이트 특화 스크래핑 로직 ✅
   - **테스트 완료**: 2개 제품, 20개 이미지 성공적으로 스크래핑 ✅

5. **Indexing 서비스 ✅ 완료**
   - requirements.txt - langchain-huggingface, pymilvus 등 패키지 ✅
   - Dockerfile - Python 3.11 컨테이너 설정 ✅
   - docker-compose.yml - 서비스 구성 ✅
   - embedding_generator.py - BGE-M3 임베딩 모델 (CPU/GPU 자동선택) ✅
   - text_chunker.py - 제품 데이터 전용 청킹 (기본정보/설명/이미지 분할) ✅
   - milvus_client.py - Milvus 벡터 스토어 (배치 처리, 검색 최적화) ✅
   - vector_indexer.py - 벡터 인덱싱 로직 ✅
   - document_preprocessor.py - 문서 전처리 ✅
   - database.py - PostgreSQL 연결 ✅
   - main.py - FastAPI 애플리케이션 (관리자 API, 백그라운드 작업) ✅
   - **테스트 완료**: 제품 데이터 청킹 및 벡터 인덱싱 성공 ✅

6. **RAG API 서비스 ✅ 완료**
   - requirements.txt - BGE-M3, pymilvus, requests 등 패키지 ✅
   - Dockerfile - Python 3.11 컨테이너 설정 ✅
   - docker-compose.yml - 서비스 구성 ✅
   - embedding_generator.py - BGE-M3 임베딩 모델 ✅
   - vector_search.py - Milvus 벡터 검색 엔진 ✅
   - llm_client.py - Ollama Gemma3 LLM 클라이언트 (스트리밍 지원) ✅
   - main.py - FastAPI 애플리케이션 (632줄) ✅
     - `/chat` - RAG 기반 질의응답 (스트리밍/일반 모드) ✅
     - `/search` - 벡터 검색 전용 API ✅
     - `/admin/login` - JWT 기반 관리자 인증 ✅
     - `/admin/stats` - 시스템 통계 ✅
     - `/admin/prompt` - 시스템 프롬프트 관리 ✅
     - `/admin/documents` - 문서 CRUD API ✅
   - **핵심 기능**: 실시간 스트리밍 응답, 디버깅 정보 제공 ✅

7. **Web App ✅ 완료**
   - docker-compose.yml - Nginx 웹서버 구성 ✅
   - index.html - 모바일 최적화 채팅 UI (670줄) ✅
     - 실시간 스트리밍 채팅 인터페이스 ✅
     - RAG 디버깅 패널 (검색 결과, 프롬프트 확인) ✅
     - 응답 소스 정보 표시 ✅
     - 타이핑 인디케이터 ✅
     - 모바일 최적화 반응형 디자인 ✅
   - admin-login.html - 관리자 로그인 페이지 ✅
   - admin.html - 관리자 대시보드 ✅
   - debug.html - 디버깅 전용 페이지 ✅

8. **시스템 관리 스크립트**
   - start.sh - 전체 시스템 시작 스크립트 ✅
   - stop.sh - 전체 시스템 종료 스크립트 ✅
   - load-env.sh - 환경변수 로딩 스크립트 ✅

### 🎯 MVP 시스템 완성 상태
- **✅ 완료된 핵심 기능들**
  - 웹 스크래핑 → PostgreSQL 저장 ✅
  - BGE-M3 임베딩 → Milvus 벡터 저장 ✅
  - 벡터 검색 → Ollama LLM → 스트리밍 응답 ✅
  - 모바일 웹 채팅 UI ✅
  - 관리자 대시보드 ✅
  - 실시간 디버깅 기능 ✅

---

## 🎉 시스템 완성 상황

### ✅ 전체 RAG LLM MVP 시스템 완료
- **🗂️ 데이터베이스 레이어**: PostgreSQL (원본 데이터) + Milvus (벡터 데이터) ✅
- **🔄 데이터 파이프라인**: 스크래핑 → 청킹 → 임베딩 → 벡터 저장 ✅  
- **🤖 AI 서비스**: BGE-M3 임베딩 + Ollama Gemma3 LLM ✅
- **🌐 웹 인터페이스**: 모바일 최적화 채팅 UI + 관리자 대시보드 ✅
- **🔧 운영 도구**: Docker 컴포즈 + 환경변수 관리 + 시스템 스크립트 ✅

### 📋 향후 확장 가능 기능 (선택사항)
- [ ] **QR 코드 생성**: 모바일 접속용 QR 코드 자동 생성
- [ ] **이미지 업로드**: 멀티모달 기능 (사용자가 제품 사진 업로드)
- [ ] **음성 인식**: 음성으로 질문하기
- [ ] **제품 추천**: 사용자 선호도 기반 제품 추천 시스템
- [ ] **다국어 지원**: 영어/중국어 등 다국어 인터페이스
- [ ] **성능 모니터링**: Grafana + Prometheus 모니터링 대시보드
- [ ] **자동 스케일링**: Kubernetes 기반 자동 확장
- [ ] **A/B 테스트**: 다양한 LLM 모델 성능 비교
- [ ] **캐싱 최적화**: Redis 기반 응답 캐싱
- [ ] **보안 강화**: OAuth 2.0 인증, HTTPS 적용

---

---

## 📊 최종 시스템 테스트 결과 

### ✅ 전체 파이프라인 검증 완료
- **스크래핑**: UNCOMMON 사이트에서 2개 제품, 20개 이미지 수집 ✅
- **데이터 저장**: PostgreSQL에 JSON 구조로 제품 데이터 저장 ✅  
- **벡터 인덱싱**: BGE-M3 모델로 제품 정보 임베딩, Milvus 저장 ✅
- **RAG 검색**: 벡터 유사도 검색으로 관련 제품 정보 추출 ✅
- **LLM 응답**: Ollama Gemma3으로 자연어 답변 생성 ✅
- **웹 UI**: 모바일 최적화 실시간 채팅 인터페이스 ✅
- **관리 기능**: JWT 인증, 시스템 모니터링, 디버깅 패널 ✅

### 🔗 서비스 접속 정보
- **사용자 채팅**: `http://localhost:3000` (모바일 최적화)
- **관리자 대시보드**: `http://localhost:3000/admin-login.html`
- **RAG API**: `http://localhost:8003` (Swagger UI: `/docs`)
- **Scraper API**: `http://localhost:8001/docs`
- **Indexing API**: `http://localhost:8002/docs`

### 🛠️ 운영 명령어
```bash
# 전체 시스템 시작
./start.sh

# 전체 시스템 종료  
./stop.sh

# 개별 서비스 시작 (환경변수 로딩 포함)
cd [service_name] && source ../load-env.sh && docker compose up -d
```

---

## 🎯 시스템 운영 가이드

### 📋 일반 사용 시나리오
1. **제품 정보 추가**: 스크래핑 API로 새 제품 수집
2. **자동 인덱싱**: 새 제품 데이터 자동으로 벡터화 
3. **사용자 질의**: 웹 채팅에서 제품 관련 질문
4. **실시간 응답**: RAG 기반 정확한 답변 제공

### 🔧 관리자 작업
- **시스템 모니터링**: `/admin/stats` API로 상태 확인
- **프롬프트 튜닝**: `/admin/prompt` API로 답변 품질 개선  
- **문서 관리**: `/admin/documents` API로 수동 문서 추가/삭제
- **디버깅**: 웹 UI의 디버깅 패널로 검색 결과 분석

### 🚀 확장 및 개선 방향
- **성능**: 더 많은 제품 데이터 수집, 임베딩 모델 업그레이드
- **기능**: QR 코드, 이미지 업로드, 음성 인식 추가
- **운영**: 모니터링 대시보드, 자동 배포 파이프라인 구축