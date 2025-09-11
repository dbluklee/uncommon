# UNCOMMON RAG LLM 시스템 시퀀스 다이어그램

## 개요
이 문서는 UNCOMMON RAG 시스템의 주요 워크플로우를 시간 순서에 따라 상세히 설명하는 시퀀스 다이어그램들을 포함합니다.

## 1. 전체 시스템 초기화 시퀀스

```mermaid
sequenceDiagram
    participant Admin as 관리자
    participant Script as start.sh
    participant Docker as Docker Engine
    participant PG as PostgreSQL
    participant MV as Milvus
    participant SC as Scraper
    participant IX as Indexing
    participant RA as RAG API
    participant WA as WebApp
    
    Admin->>+Script: ./start.sh 실행
    Script->>+Docker: 네트워크 생성
    Docker-->>-Script: uncommon_rag-network 생성됨
    
    par 데이터베이스 서비스 시작
        Script->>+PG: PostgreSQL 컨테이너 시작
        PG->>PG: 데이터베이스 초기화
        PG->>PG: 테이블 생성 (products, product_images, scraping_jobs)
        PG-->>-Script: 준비 완료
    and
        Script->>+MV: Milvus 의존성 시작 (etcd, minio)
        MV->>MV: etcd 클러스터 초기화
        MV->>MV: MinIO 객체 스토리지 시작
        MV->>MV: Milvus 서버 시작
        MV-->>-Script: 벡터 DB 준비 완료
    end
    
    par API 서비스 시작
        Script->>+SC: Scraper 서비스 시작
        SC->>SC: FastAPI 앱 초기화
        SC->>PG: DB 연결 테스트
        SC-->>-Script: 스크래퍼 준비 완료
    and
        Script->>+IX: Indexing 서비스 시작
        IX->>IX: BGE-M3 모델 로딩
        IX->>PG: DB 연결 설정
        IX->>MV: Milvus 연결 설정
        IX-->>-Script: 인덱싱 서비스 준비 완료
    and
        Script->>+RA: RAG API 서비스 시작
        RA->>RA: BGE-M3 모델 로딩
        RA->>RA: Router LLM 클라이언트 초기화
        RA->>MV: 벡터 스토어 연결
        RA-->>-Script: RAG API 준비 완료
    end
    
    Script->>+WA: 웹앱 시작
    WA->>WA: Nginx 서버 시작
    WA-->>-Script: 웹 UI 준비 완료
    
    Script-->>-Admin: 모든 서비스 시작 완료
```

## 2. 제품 스크래핑 워크플로우

```mermaid
sequenceDiagram
    participant User as 사용자
    participant SC as Scraper Service
    participant Target as UNCOMMON 웹사이트
    participant PG as PostgreSQL
    participant IX as Indexing Service
    participant BG as Background Task
    
    User->>+SC: POST /scrape 요청
    SC->>PG: 실행 중인 작업 확인
    PG-->>SC: 중복 작업 없음
    
    SC->>PG: 새 스크래핑 작업 생성
    PG-->>SC: job_id 반환
    SC-->>-User: 작업 시작 응답 (job_id)
    
    SC->>+BG: 백그라운드 스크래핑 시작
    BG->>PG: 작업 상태 → 'running' 업데이트
    
    loop 제품 페이지별 스크래핑
        BG->>+Target: HTTP 요청 (제품 목록)
        Target-->>-BG: HTML 응답
        BG->>BG: BeautifulSoup 파싱
        
        loop 각 제품별 처리
            BG->>+Target: 제품 상세 페이지 요청
            Target-->>-BG: 제품 상세 HTML
            BG->>BG: 제품 정보 추출 (이름, 가격, 색상, 재질, 사이즈)
            
            par 이미지 다운로드
                BG->>+Target: 제품 이미지 요청 (영문 사이트)
                Target-->>-BG: 이미지 바이너리
            and
                BG->>+Target: 제품 이미지 요청 (한글 사이트)
                Target-->>-BG: 이미지 바이너리
            end
            
            BG->>+PG: 제품 데이터 저장
            PG->>PG: products 테이블 INSERT
            PG->>PG: product_images 테이블 INSERT (바이너리)
            PG-->>-BG: 저장 완료
        end
    end
    
    BG->>PG: 작업 상태 → 'completed' 업데이트
    BG->>+IX: POST /process/new-products (알림)
    IX-->>-BG: 인덱싱 시작 확인
    BG-->>-SC: 스크래핑 완료
```

## 3. 벡터 인덱싱 워크플로우

```mermaid
sequenceDiagram
    participant SC as Scraper Service
    participant IX as Indexing Service
    participant PG as PostgreSQL
    participant BGE as BGE-M3 Model
    participant MV as Milvus DB
    participant TC as TextChunker
    
    SC->>+IX: POST /process/new-products
    IX->>PG: 인덱싱되지 않은 제품 조회
    PG-->>IX: 제품 목록 반환
    
    loop 각 제품별 인덱싱
        IX->>+PG: 제품 상세 정보 조회
        PG-->>-IX: 제품 데이터 + 이미지 메타데이터
        
        IX->>+TC: 제품 데이터 청킹 요청
        TC->>TC: 제품명 청크 생성
        TC->>TC: 설명 청크 생성
        TC->>TC: 재질/사이즈 청크 생성
        TC->>TC: 이미지 메타데이터 청크 생성
        TC-->>-IX: 청크 리스트 반환
        
        loop 각 청크별 임베딩
            IX->>+BGE: 텍스트 임베딩 생성 요청
            BGE->>BGE: CUDA GPU 가속 처리
            BGE->>BGE: 1024차원 벡터 생성
            BGE-->>-IX: 임베딩 벡터 반환
            
            IX->>+MV: 벡터 + 메타데이터 저장
            MV->>MV: HNSW 인덱스 업데이트
            MV-->>-IX: 저장 완료
        end
        
        IX->>+PG: 제품 인덱싱 상태 업데이트
        PG->>PG: indexed = true, indexed_at = now()
        PG-->>-IX: 업데이트 완료
    end
    
    IX-->>-SC: 인덱싱 완료 응답
```

## 4. 조건부 RAG 질의응답 워크플로우

```mermaid
sequenceDiagram
    participant User as 사용자
    participant WA as 웹앱 (브라우저)
    participant RA as RAG API
    participant RT as Router LLM
    participant MV as Milvus DB
    participant EXT as 외부 Ollama LLM
    participant PG as PostgreSQL
    
    User->>+WA: 질문 입력 + 전송
    WA->>+RA: POST /chat (스트리밍 요청)
    
    Note over RA: 1단계: RAG 필요성 판단
    RA->>+RT: 질문 분석 요청
    RT->>RT: 질문이 제품 정보 관련인가?
    RT-->>-RA: RAG 필요/불필요 판단 결과
    
    alt RAG 불필요 (일반 질문)
        RA->>+RT: 직접 응답 생성 요청
        RT->>RT: 일반 지식 기반 답변 생성
        RT-->>-RA: 생성된 답변
        RA-->>WA: 스트리밍 응답 (직접)
    else RAG 필요 (제품 관련 질문)
        Note over RA: 2단계: 벡터 검색
        RA->>RA: 질문 임베딩 생성 (BGE-M3)
        RA->>+MV: 유사 벡터 검색 (top_k=5)
        MV->>MV: COSINE 유사도 계산
        MV->>MV: HNSW 인덱스 탐색
        MV-->>-RA: 유사 문서 리스트
        
        alt 검색 결과 없음
            RA-->>WA: "관련 제품을 찾을 수 없습니다" 응답
        else 검색 결과 있음
            Note over RA: 3단계: 컨텍스트 구성
            RA->>RA: 검색 결과를 컨텍스트로 구성
            
            opt 이미지 정보 포함 시
                RA->>+PG: 제품 이미지 메타데이터 조회
                PG-->>-RA: 이미지 정보 반환
            end
            
            Note over RA: 4단계: LLM 생성
            RA->>+EXT: 프롬프트 + 컨텍스트 전송
            EXT->>EXT: Gemma3 27B 모델 추론
            EXT-->>-RA: 생성된 답변 (스트리밍)
            
            RA-->>WA: 검색 결과 + 스트리밍 응답
        end
    end
    
    WA-->>-User: 실시간 답변 표시
```

## 5. 멀티모달 이미지 업로드 및 처리

```mermaid
sequenceDiagram
    participant User as 사용자
    participant WA as 웹앱
    participant RA as RAG API
    participant FileHandler as 파일 처리
    participant MV as Milvus
    participant EXT as 외부 Ollama
    
    User->>+WA: 이미지 파일 드래그&드롭
    WA->>WA: 파일 유효성 검사 (크기, 형식)
    WA->>WA: 이미지 미리보기 생성
    WA-->>User: 미리보기 표시
    
    User->>WA: 질문 + 이미지와 함께 전송
    WA->>+RA: POST /chat/multimodal (FormData)
    
    RA->>+FileHandler: 이미지 파일 처리
    FileHandler->>FileHandler: 파일 크기 검증 (10MB 한도)
    FileHandler->>FileHandler: MIME 타입 검증
    FileHandler->>FileHandler: 이미지 메타데이터 추출
    FileHandler-->>-RA: 처리된 이미지 데이터
    
    par 벡터 검색
        RA->>RA: 텍스트 질문 임베딩 생성
        RA->>+MV: 벡터 검색 수행
        MV-->>-RA: 관련 제품 정보 반환
    and 이미지 분석 준비
        RA->>RA: 이미지를 Base64 인코딩
        RA->>RA: 멀티모달 프롬프트 구성
    end
    
    RA->>+EXT: 텍스트 + 이미지 + 컨텍스트 전송
    EXT->>EXT: 멀티모달 LLM 추론
    Note over EXT: 이미지 내용 분석 + 제품 정보 결합
    EXT-->>-RA: 생성된 답변 (스트리밍)
    
    RA-->>-WA: 멀티모달 응답 스트리밍
    WA-->>-User: 이미지 기반 답변 표시
```

## 6. 실시간 스트리밍 응답 처리

```mermaid
sequenceDiagram
    participant Browser as 브라우저 JavaScript
    participant SSE as Server-Sent Events
    participant RA as RAG API
    participant AsyncGen as 비동기 생성기
    participant LLM as LLM Service
    
    Browser->>+RA: POST /chat (stream=true)
    RA->>+AsyncGen: 스트리밍 생성기 생성
    RA-->>Browser: HTTP 200 + Content-Type: text/event-stream
    
    AsyncGen->>+SSE: 스트리밍 시작
    SSE-->>Browser: data: {"type": "start", "sources": [...]}
    
    loop LLM 토큰 생성
        AsyncGen->>+LLM: 다음 토큰 요청
        LLM-->>-AsyncGen: 생성된 토큰
        AsyncGen->>SSE: 토큰 데이터 전송
        SSE-->>Browser: data: {"type": "content", "content": "토큰"}
        Browser->>Browser: UI 실시간 업데이트
        
        Note over AsyncGen: 백프레셔 제어
        AsyncGen->>AsyncGen: await asyncio.sleep(0.01)
    end
    
    AsyncGen->>SSE: 스트리밍 종료
    SSE-->>Browser: data: {"type": "end"}
    AsyncGen-->>-RA: 생성 완료
    RA-->>-Browser: 연결 종료
    
    Browser->>Browser: 최종 메시지 완성 및 UI 정리
```

## 7. 디버깅 정보 수집 및 표시

```mermaid
sequenceDiagram
    participant User as 개발자
    participant Debug as 디버그 패널
    participant RA as RAG API
    participant MV as Milvus
    participant LLM as LLM Service
    
    User->>RA: POST /chat (include_debug=true)
    
    RA->>RA: 디버깅 정보 수집 시작
    RA->>MV: 벡터 검색 수행
    MV-->>RA: 검색 결과 + 유사도 점수
    
    RA->>RA: 디버깅 객체 생성
    Note over RA: 수집 정보:<br/>- 사용자 질문<br/>- 검색 결과 상세<br/>- 프롬프트 템플릿<br/>- LLM 설정값
    
    RA->>+LLM: LLM 요청 + 설정 로깅
    LLM-->>-RA: 응답 + 처리 시간
    
    RA-->>Debug: SSE로 디버깅 정보 전송
    Note over Debug: 실시간 패널 업데이트:<br/>- 검색된 제품 목록<br/>- 유사도 점수<br/>- 사용된 프롬프트<br/>- 처리 시간 통계
    
    Debug-->>User: 시각화된 디버깅 정보 표시
```

## 8. 시스템 헬스체크 및 모니터링

```mermaid
sequenceDiagram
    participant Monitor as 모니터링 도구
    participant WA as WebApp
    participant RA as RAG API
    participant IX as Indexing
    participant SC as Scraper
    participant PG as PostgreSQL
    participant MV as Milvus
    
    par 주기적 헬스체크 (30초 간격)
        Monitor->>+WA: GET /health
        WA->>WA: Nginx 상태 확인
        WA-->>-Monitor: {"status": "healthy"}
    and
        Monitor->>+RA: GET /health
        RA->>RA: 서비스 상태 확인
        RA-->>-Monitor: {"status": "healthy"}
    and
        Monitor->>+IX: GET /health
        IX->>IX: BGE-M3 모델 상태 확인
        IX-->>-Monitor: {"status": "healthy"}
    and
        Monitor->>+SC: GET /health
        SC->>SC: 스크래퍼 상태 확인
        SC-->>-Monitor: {"status": "healthy"}
    end
    
    alt 서비스 다운 감지
        Monitor->>Monitor: 알람 트리거
        Monitor->>Monitor: 복구 시도 또는 알림 발송
    else 모든 서비스 정상
        Monitor->>+RA: GET /stats
        RA->>+MV: 벡터 DB 통계 조회
        MV-->>-RA: 벡터 수, 인덱스 상태
        RA->>+PG: 제품 DB 통계 조회
        PG-->>-RA: 총 제품 수, 인덱싱 완료 수
        RA-->>-Monitor: 종합 통계 정보
    end
```

## 9. 오류 처리 및 복구 시퀀스

```mermaid
sequenceDiagram
    participant User as 사용자
    participant RA as RAG API
    participant EXT as 외부 LLM 서버
    participant MV as Milvus
    participant Fallback as 폴백 처리
    
    User->>+RA: POST /chat 요청
    
    RA->>+MV: 벡터 검색 요청
    
    alt Milvus 연결 실패
        MV--x RA: 연결 타임아웃 오류
        RA->>+Fallback: 폴백 모드 활성화
        Fallback->>Fallback: 캐시된 응답 확인
        Fallback-->>-RA: 일반적인 안내 메시지
        RA-->>User: "일시적 오류, 다시 시도해주세요"
    else 벡터 검색 성공
        MV-->>-RA: 검색 결과 반환
        
        RA->>+EXT: LLM 생성 요청
        
        alt 외부 LLM 서버 오류
            EXT--x RA: HTTP 503 Service Unavailable
            RA->>+Fallback: 대체 응답 생성
            Fallback->>Fallback: 템플릿 기반 응답 생성
            Fallback-->>-RA: "현재 AI 서비스가 일시적으로 불안정합니다"
            RA-->>User: 폴백 응답
        else LLM 정상 처리
            EXT-->>-RA: 생성된 응답
            RA-->>-User: 정상 응답
        end
    end
```

## 10. 시스템 종료 시퀀스

```mermaid
sequenceDiagram
    participant Admin as 관리자
    participant Script as stop.sh
    participant Docker as Docker Engine
    participant Services as 모든 서비스
    participant Volumes as 데이터 볼륨
    
    Admin->>+Script: ./stop.sh 실행
    
    Script->>+Docker: 실행 중인 컨테이너 확인
    Docker-->>-Script: 컨테이너 목록
    
    par 서비스 정상 종료
        Script->>+Services: SIGTERM 신호 전송
        Services->>Services: 현재 요청 완료 대기
        Services->>Services: 연결 정리
        Services->>Services: 리소스 해제
        Services-->>-Script: 정상 종료 완료
    end
    
    Script->>+Docker: 네트워크 정리
    Docker->>Docker: uncommon_rag-network 제거
    Docker-->>-Script: 네트워크 제거 완료
    
    opt 데이터 보존 확인
        Script->>+Volumes: 볼륨 상태 확인
        Volumes-->>-Script: PostgreSQL/Milvus 데이터 보존 확인
    end
    
    Script-->>-Admin: 시스템 종료 완료
```

이러한 시퀀스 다이어그램들은 시스템의 동작 방식을 시간 순서대로 명확히 보여주며, 각 구성 요소 간의 상호작용과 데이터 흐름을 이해하는 데 도움이 됩니다.