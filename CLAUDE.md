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