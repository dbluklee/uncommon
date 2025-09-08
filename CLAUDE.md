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

## 🚀 시스템 시작 명령
```bash
# 1. 네트워크 생성
docker network create rag-network

# 2. 데이터베이스 시작
cd PostgreSQLDB && docker-compose up -d
cd ../MilvusDB && docker-compose up -d

# 3. 서비스 시작
cd ../scraper && docker-compose up -d
cd ../indexing && docker-compose up -d
cd ../rag-api && docker-compose up -d
cd ../webapp && docker-compose up -d
```

## 📌 개발 시 주의사항
1. 모든 서비스는 Docker 컨테이너로 실행
2. 환경변수는 .env.global과 각 서비스별 .env 파일로 관리
3. BGE-M3 임베딩 모델은 첫 실행 시 자동 다운로드
4. Ollama는 외부 서버(112.148.37.41:1884)에서 실행 중
5. 관리자 API는 ADMIN_API_KEY로 인증

---

## 📊 현재 개발 진행 상황 (2024-09-08)

### ✅ 완료된 작업
1. **프로젝트 기본 구조**
   - CLAUDE.md 파일 생성 및 계획 문서화
   - .env.global 전역 환경변수 설정
   - 프로젝트 폴더 구조 생성

2. **PostgreSQL 데이터베이스**
   - Docker 구성 (PostgreSQLDB/docker-compose.yml)
   - 스키마 정의 (init.sql) - 제품 중심 구조
   - 환경변수 설정 (.env)

3. **Milvus 벡터 데이터베이스**
   - Docker 구성 (MilvusDB/docker-compose.yml)
   - 환경변수 설정 (.env)

4. **Scraper 서비스 ✅ 완료**
   - requirements.txt - 필요한 패키지 정의 ✅
   - Dockerfile - Python 컨테이너 설정 ✅
   - docker-compose.yml - 서비스 구성 ✅
   - 환경변수 설정 (.env) ✅
   - main.py - FastAPI 애플리케이션 ✅
   - database.py - PostgreSQL 연결 ✅
   - models.py - SQLAlchemy 모델 ✅
   - scraper.py - 스크래핑 로직 ✅
   - **테스트 완료**: 2개 제품, 20개 이미지 성공적으로 스크래핑 ✅

5. **시스템 관리 스크립트**
   - start.sh - 전체 시스템 시작
   - stop.sh - 전체 시스템 종료

### 🚧 현재 작업 중
- **Scraper 서비스 완료 ✅**
- **다음: Indexing 서비스 개발**

---

## 📋 향후 개발 Todo 리스트

### ✅ 1. Scraper 서비스 완성
- [x] **database.py** - PostgreSQL 연결 설정
- [x] **models.py** - SQLAlchemy 모델 (Product, ProductImage, ScrapingJob)  
- [x] **scraper.py** - 제품 스크래핑 로직 구현
  - [x] BeautifulSoup4로 HTML 파싱
  - [x] 제품 정보 추출 (이름, 가격, 재질, 특징 등)
  - [x] 이미지 다운로드 및 바이너리 저장
  - [x] JSON 형태로 제품 데이터 구조화
  - [x] IP 차단 방지 (User-Agent 로테이션, 랜덤 지연)
  - [x] UNCOMMON 사이트 특화 파싱 로직
- [x] **main.py** - FastAPI 애플리케이션 완성
  - [x] 관리자 인증 구현
  - [x] `/admin/scrape` API 엔드포인트
  - [x] `/admin/jobs` 작업 상태 조회 API
  - [x] `/admin/products` 제품 목록 조회 API
  - [x] `/admin/stats` 시스템 통계 API
  - [x] 백그라운드 스크래핑 작업 처리
- [x] **테스트 검증 완료**
  - [x] 2개 제품 성공적으로 스크래핑
  - [x] 20개 이미지 PostgreSQL 저장
  - [x] JSON 구조로 제품 데이터 저장

### 2. Indexing 서비스 구현
- [ ] **requirements.txt** - BGE-M3, Milvus 등 패키지
- [ ] **Dockerfile** - Python 환경 설정
- [ ] **docker-compose.yml** - 서비스 구성
- [ ] **database.py** - PostgreSQL 연결
- [ ] **models.py** - 데이터 모델
- [ ] **processor.py** - BGE-M3 임베딩 처리
  - [ ] CUDA 사용 설정 (USE_CUDA 환경변수)
  - [ ] 텍스트 청킹 (CHUNK_SIZE=500)
  - [ ] 배치 처리 (EMBEDDING_BATCH_SIZE=32)
- [ ] **milvus_client.py** - Milvus 연결 및 벡터 저장
- [ ] **main.py** - FastAPI 애플리케이션
  - [ ] `/process/new-products` - 새 제품 처리 API
  - [ ] `/index/status` - 인덱싱 상태 API

### 3. RAG API 서비스 구현
- [ ] **requirements.txt** - BGE-M3, Milvus, requests 등
- [ ] **Dockerfile** - Python 환경
- [ ] **docker-compose.yml** - 서비스 구성
- [ ] **rag_engine.py** - RAG 핵심 로직
  - [ ] BGE-M3 쿼리 임베딩 생성
  - [ ] Milvus 유사도 검색 (TOP_K=5)
  - [ ] Ollama Gemma3 API 연동
  - [ ] 컨텍스트 구성 및 응답 생성
- [ ] **main.py** - FastAPI 애플리케이션
  - [ ] `/chat` - 일반 질문 응답
  - [ ] `/chat/stream` - 스트리밍 응답
  - [ ] 이미지 업로드 처리 (멀티모달)

### 4. Web App 구현
- [ ] **requirements.txt** 또는 **package.json**
- [ ] **Dockerfile** - 웹서버 환경
- [ ] **docker-compose.yml** - 서비스 구성
- [ ] **index.html** - 메인 페이지
  - [ ] 모바일 최적화 UI
  - [ ] QR 코드 표시
  - [ ] 채팅 인터페이스
- [ ] **app.js** - 프론트엔드 로직
  - [ ] RAG API 통신
  - [ ] 이미지 업로드 기능
  - [ ] 스트리밍 응답 처리
- [ ] **style.css** - 반응형 스타일

### 5. 시스템 통합 및 테스트
- [ ] 전체 시스템 통합 테스트
- [ ] 스크래핑 → 인덱싱 → 검색 파이프라인 검증
- [ ] 에러 처리 및 로깅 개선
- [ ] 성능 최적화

---

---

## 📊 스크래핑 테스트 결과 (2025-09-08)

### ✅ 성공적으로 완료된 테스트
- **스크래핑 대상**: `https://ucmeyewear.earth/category/all/87/`
- **발견된 제품 링크**: 36개
- **테스트 스크래핑**: 2개 제품
- **총 이미지**: 20개 (제품당 10개)
- **소요시간**: 약 26초

### 스크래핑된 제품 데이터
1. **WAVE 0.01 (BLACK)** - $170.00
2. **WAVE 0.02 (BLACK)** - $170.00

### 검증된 기능
- ✅ 환경변수 관리 (.env.global)
- ✅ 포트 충돌 방지 (PostgreSQL: 5434, Scraper: 8011)
- ✅ 컨테이너 네이밍 (uncommon_ 접두사)
- ✅ IP 차단 방지 메커니즘
- ✅ JSON 구조화된 데이터 저장
- ✅ 이미지 바이너리 DB 저장
- ✅ 관리자 API 인증 및 상태 조회

---

## 🎯 다음 개발 세션 시작점
**Indexing 서비스 개발 시작**
1. `indexing/requirements.txt` - BGE-M3, Milvus 패키지
2. `indexing/Dockerfile` - Python 환경 설정  
3. `indexing/main.py` - FastAPI 애플리케이션
4. `indexing/processor.py` - BGE-M3 임베딩 처리
5. `indexing/milvus_client.py` - Milvus 연결 및 벡터 저장

**현재 실행 중인 서비스:**
- PostgreSQL: `localhost:5434` (uncommon_rag-postgres)
- Scraper API: `localhost:8011` (uncommon_rag-scraper)

**다음 구현 목표:**
- PostgreSQL에서 제품 데이터 읽기
- BGE-M3로 텍스트 임베딩 생성
- Milvus에 벡터 저장