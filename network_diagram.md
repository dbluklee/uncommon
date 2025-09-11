# UNCOMMON RAG LLM 시스템 네트워크 다이어그램

## 네트워크 토폴로지 개요

시스템은 Docker 브릿지 네트워크 `uncommon_rag-network`를 기반으로 구성되며, 외부 접근 포트와 내부 통신 포트를 분리하여 보안성과 확장성을 확보했습니다.

## 전체 네트워크 아키텍처

```mermaid
graph TB
    subgraph "외부 네트워크 (Internet)"
        USER[👤 사용자<br>브라우저]
        EXTERNAL_LLM[🤖 외부 Ollama 서버<br>112.148.37.41:1884<br>Gemma3 27B]
        TARGET_SITE[🌐 UNCOMMON 안경몰<br>ucmeyewear.earth]
    end
    
    subgraph "Docker Host (Host Network)"
        subgraph "외부 접근 포트"
            PORT_3000[":3000<br>웹 UI"]
            PORT_8001[":8001<br>Scraper API"]
            PORT_8002[":8002<br>Indexing API"]
            PORT_8003[":8003<br>RAG API"]
            PORT_5434[":5434<br>PostgreSQL"]
            PORT_19532[":19532<br>Milvus"]
            PORT_11435[":11435<br>Router Ollama"]
        end
    end
    
    subgraph "Docker Bridge Network: uncommon_rag-network"
        subgraph "웹 서비스 레이어"
            WEBAPP[uncommon_rag-webapp<br>Nginx:80<br>📱 모바일 UI]
        end
        
        subgraph "API 서비스 레이어"
            SCRAPER[uncommon_rag-scraper<br>FastAPI:8000<br>🕷️ 웹 스크래핑]
            INDEXING[uncommon_rag-indexing<br>FastAPI:8000<br>🔍 벡터 인덱싱]
            RAG_API[uncommon_rag-api<br>FastAPI:8000<br>🧠 질의응답 엔진]
            ROUTER_OLLAMA[uncommon_router-ollama<br>Ollama:11434<br>🎯 RAG 라우터]
        end
        
        subgraph "데이터 서비스 레이어"
            POSTGRES[uncommon_rag-postgres<br>PostgreSQL:5432<br>🗄️ 제품 DB]
            MILVUS[uncommon_rag-milvus<br>Milvus:19530<br>🧮 벡터 DB]
            ETCD[milvus-etcd<br>etcd:2379<br>📋 Milvus 메타데이터]
            MINIO[milvus-minio<br>MinIO:9000<br>💾 객체 저장소]
        end
    end
    
    %% 외부 접근
    USER --> PORT_3000
    USER --> PORT_8001
    USER --> PORT_8002
    USER --> PORT_8003
    
    %% 포트 포워딩
    PORT_3000 --> WEBAPP
    PORT_8001 --> SCRAPER
    PORT_8002 --> INDEXING
    PORT_8003 --> RAG_API
    PORT_5434 --> POSTGRES
    PORT_19532 --> MILVUS
    PORT_11435 --> ROUTER_OLLAMA
    
    %% 내부 서비스 간 통신
    WEBAPP -.->|HTTP API 호출| RAG_API
    WEBAPP -.->|관리 요청| SCRAPER
    SCRAPER -->|제품 데이터 저장| POSTGRES
    SCRAPER -.->|인덱싱 트리거| INDEXING
    INDEXING -->|제품 조회| POSTGRES
    INDEXING -->|벡터 저장| MILVUS
    RAG_API -->|RAG 판단| ROUTER_OLLAMA
    RAG_API -->|벡터 검색| MILVUS
    RAG_API -->|이미지 조회| POSTGRES
    
    %% 외부 연결
    SCRAPER -->|웹 스크래핑| TARGET_SITE
    RAG_API -.->|LLM 요청| EXTERNAL_LLM
    
    %% Milvus 내부 의존성
    MILVUS --> ETCD
    MILVUS --> MINIO
    
    style USER fill:#e3f2fd
    style EXTERNAL_LLM fill:#fff3e0
    style TARGET_SITE fill:#fff3e0
    style WEBAPP fill:#e8f5e8
    style SCRAPER fill:#fff8e1
    style INDEXING fill:#fff8e1
    style RAG_API fill:#fff8e1
    style ROUTER_OLLAMA fill:#fff8e1
    style POSTGRES fill:#fce4ec
    style MILVUS fill:#fce4ec
    style ETCD fill:#f3e5f5
    style MINIO fill:#f3e5f5
```

## 네트워크 설정 세부사항

### Docker 네트워크 구성
```yaml
networks:
  uncommon_rag-network:
    driver: bridge
    name: uncommon_rag-network
```

### 포트 매핑 전략

| 서비스 | 외부 포트 | 내부 포트 | 프로토콜 | 목적 |
|--------|----------|----------|----------|------|
| 웹 앱 | 3000 | 80 | HTTP | 사용자 인터페이스 |
| Scraper API | 8001 | 8000 | HTTP | 스크래핑 관리 |
| Indexing API | 8002 | 8000 | HTTP | 벡터 인덱싱 |
| RAG API | 8003 | 8000 | HTTP | 질의응답 서비스 |
| PostgreSQL | 5434 | 5432 | TCP | 데이터베이스 접근 |
| Milvus | 19532 | 19530 | gRPC | 벡터 검색 |
| Router Ollama | 11435 | 11434 | HTTP | 내부 LLM |

## 서비스 간 통신 패턴

### 1. 사용자 요청 플로우
```mermaid
sequenceDiagram
    participant U as 사용자 브라우저
    participant W as WebApp (Nginx)
    participant R as RAG API (FastAPI)
    participant M as Milvus
    participant O as 외부 Ollama
    
    U->>+W: HTTP GET / (포트 3000)
    W-->>-U: HTML/CSS/JS 응답
    
    U->>+R: POST /chat (포트 8003)
    R->>+M: 벡터 검색 (내부 19530)
    M-->>-R: 유사 문서 반환
    R->>+O: LLM 생성 요청 (외부 1884)
    O-->>-R: 생성된 응답
    R-->>-U: 스트리밍 응답 (SSE)
```

### 2. 스크래핑 및 인덱싱 플로우
```mermaid
sequenceDiagram
    participant A as 관리자
    participant S as Scraper Service
    participant P as PostgreSQL
    participant I as Indexing Service
    participant M as Milvus
    participant T as 타겟 사이트
    
    A->>+S: POST /scrape (포트 8001)
    S->>+T: HTTP 스크래핑 요청
    T-->>-S: HTML 응답
    S->>+P: 제품 데이터 저장 (내부 5432)
    P-->>-S: 저장 완료
    S->>+I: POST /process/new-products (내부 8000)
    I->>+P: 제품 데이터 조회
    P-->>-I: 제품 정보 반환
    I->>+M: 벡터 저장 (내부 19530)
    M-->>-I: 인덱싱 완료
    I-->>-S: 처리 완료 알림
    S-->>-A: 스크래핑 완료 응답
```

## 네트워크 보안 및 격리

### 현재 보안 설정 (MVP 단계)
- **네트워크 격리**: Docker 브릿지 네트워크로 서비스 간 격리
- **포트 노출**: 필요한 서비스만 외부 포트 매핑
- **내부 통신**: 컨테이너 이름 기반 DNS 해석

### 내부 서비스 통신 (컨테이너 간)
```mermaid
graph LR
    subgraph "Docker DNS 해석"
        A[uncommon_rag-api] --> B[uncommon_rag-milvus]
        A --> C[uncommon_rag-postgres]
        A --> D[uncommon_router-ollama]
        E[uncommon_rag-scraper] --> C
        E --> F[uncommon_rag-indexing]
        F --> C
        F --> B
    end
```

## 데이터 플로우 네트워크 다이어그램

### 실시간 채팅 데이터 플로우
```mermaid
graph TD
    subgraph "클라이언트 사이드"
        UI[사용자 인터페이스<br>JavaScript]
        SSE[Server-Sent Events<br>실시간 스트림]
    end
    
    subgraph "네트워크 계층"
        HTTP[HTTP/1.1 연결<br>포트 8003]
        WS[WebSocket 대안<br>SSE 스트리밍]
    end
    
    subgraph "서버 사이드"
        API[RAG API 서비스<br>FastAPI AsyncIO]
        STREAM[스트리밍 생성기<br>yield 패턴]
    end
    
    UI --> HTTP
    HTTP --> API
    API --> STREAM
    STREAM --> WS
    WS --> SSE
    SSE --> UI
```

### 이미지 업로드 네트워크 플로우
```mermaid
graph TB
    subgraph "이미지 업로드 플로우"
        UP[파일 업로드<br>multipart/form-data] 
        VAL[파일 검증<br>크기/형식 확인]
        PROC[이미지 처리<br>리사이징/최적화]
        STORE[저장소 선택<br>PostgreSQL BYTEA]
    end
    
    subgraph "네트워크 레이어"
        NGINX[Nginx 프록시<br>client_max_body_size]
        FASTAPI[FastAPI 서버<br>File Upload Handler]
    end
    
    UP --> NGINX
    NGINX --> FASTAPI
    FASTAPI --> VAL
    VAL --> PROC
    PROC --> STORE
```

## 네트워크 성능 최적화

### 1. 커넥션 풀링
```yaml
# PostgreSQL 연결 풀 설정
DB_POOL_SIZE: 10
DB_MAX_OVERFLOW: 20
DB_POOL_TIMEOUT: 30
DB_POOL_RECYCLE: 3600
```

### 2. HTTP 연결 최적화
```yaml
# FastAPI/Uvicorn 설정
UVICORN_WORKERS: 4
UVICORN_KEEP_ALIVE: 5
UVICORN_TIMEOUT_KEEP_ALIVE: 5
```

### 3. 내부 서비스 검색 최적화
- **DNS 캐싱**: Docker 내장 DNS 활용
- **헬스체크**: 각 서비스별 `/health` 엔드포인트
- **로드밸런싱**: Nginx upstream 설정 준비

## 모니터링 및 로깅

### 네트워크 모니터링 포인트
```mermaid
graph TB
    subgraph "모니터링 대상"
        LB[로드밸런서 메트릭<br>Nginx 액세스 로그]
        API[API 응답 시간<br>FastAPI 미들웨어]
        DB[DB 연결 상태<br>PostgreSQL/Milvus 로그]
        EXT[외부 서비스 상태<br>Ollama 연결 모니터링]
    end
    
    subgraph "로그 수집"
        DOC[Docker 로그<br>컨테이너별 로그 스트림]
        AGG[로그 집계<br>중앙화 필요]
    end
    
    LB --> DOC
    API --> DOC
    DB --> DOC
    EXT --> DOC
    DOC --> AGG
```

## 확장성 및 고가용성

### 수평 확장 계획
```mermaid
graph TB
    subgraph "현재 구조 (단일 노드)"
        SINGLE[Docker Compose<br>단일 호스트]
    end
    
    subgraph "확장 구조 (멀티 노드)"
        K8S[Kubernetes 클러스터<br>멀티 호스트]
        LB[로드밸런서<br>HAProxy/Nginx]
        CACHE[분산 캐시<br>Redis Cluster]
    end
    
    SINGLE -.-> K8S
    K8S --> LB
    K8S --> CACHE
```

### 백업 및 복구 네트워크
- **PostgreSQL**: 마스터-슬레이브 복제 설정
- **Milvus**: 분산 클러스터 구성
- **설정 백업**: Git 기반 형상 관리

## 트러블슈팅 가이드

### 네트워크 연결 문제 진단
```bash
# 1. 컨테이너 네트워크 상태 확인
docker network ls
docker network inspect uncommon_rag-network

# 2. 서비스 간 연결 테스트
docker exec uncommon_rag-api curl http://uncommon_rag-milvus:19530/health
docker exec uncommon_rag-api curl http://uncommon_rag-postgres:5432

# 3. 포트 리스닝 상태 확인
netstat -tlnp | grep -E "(3000|8001|8002|8003|5434|19532)"

# 4. DNS 해석 테스트
docker exec uncommon_rag-api nslookup uncommon_rag-milvus
```

### 일반적인 네트워크 이슈
1. **포트 충돌**: 다른 서비스와의 포트 충돌
2. **방화벽 설정**: 호스트 방화벽 정책
3. **DNS 해석 실패**: Docker 네트워크 설정 오류
4. **타임아웃**: 외부 서비스 연결 시간 초과

이 네트워크 다이어그램은 시스템의 모든 네트워크 연결과 데이터 플로우를 명확히 보여주며, 확장성과 트러블슈팅을 고려한 구조로 설계되었습니다.