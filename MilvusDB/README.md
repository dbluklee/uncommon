# Milvus 벡터 데이터베이스

## 📋 개요
UNCOMMON RAG 시스템의 벡터 데이터베이스로, 제품 정보의 임베딩 벡터를 저장하고 유사도 기반 검색을 제공합니다.

## 🎯 주요 기능
- **벡터 저장**: 1024차원 BGE-M3 임베딩 벡터 저장
- **유사도 검색**: COSINE 거리 기반 유사 제품 검색
- **실시간 인덱싱**: 새로운 제품 벡터 즉시 추가
- **스케일링**: 대용량 벡터 데이터 효율적 처리

## 🔧 설정 및 실행

### 환경변수
```bash
MILVUS_HOST=uncommon_rag-milvus
MILVUS_PORT=19532           # 외부 접근 포트
MILVUS_INTERNAL_PORT=19530  # 컨테이너 내부 포트
MILVUS_METRICS_PORT=9093    # 메트릭 포트
COLLECTION_NAME=uncommon_products
DIMENSION=1024              # BGE-M3 임베딩 차원
METRIC_TYPE=COSINE         # 유사도 계산 방식
```

### 실행 명령
```bash
# Milvus 시작
cd MilvusDB
source ../.env.global
docker compose up -d

# 상태 확인
docker compose ps
docker compose logs -f milvus-standalone
```

### 접속 정보
- **외부 접속**: `localhost:19532`
- **내부 접속**: `uncommon_rag-milvus:19530`
- **메트릭**: `localhost:9093`

## 📊 데이터 구조

### 컬렉션 스키마
```python
collection_schema = {
    "fields": [
        {
            "name": "id",
            "type": "INT64",
            "is_primary": True,
            "auto_id": False
        },
        {
            "name": "product_id", 
            "type": "INT64"
        },
        {
            "name": "text_content",
            "type": "VARCHAR",
            "max_length": 65535
        },
        {
            "name": "embedding",
            "type": "FLOAT_VECTOR",
            "dim": 1024
        }
    ]
}
```

### 인덱스 설정
```python
index_params = {
    "metric_type": "COSINE",    # 코사인 유사도
    "index_type": "IVF_FLAT",   # 인덱스 타입
    "params": {
        "nlist": 1024           # 클러스터 수
    }
}
```

## 📥 입력 데이터 형식

### 벡터 삽입
```python
# 단일 벡터 삽입
insert_data = {
    "id": 1,
    "product_id": 123,
    "text_content": "UNCOMMON 티타늄 안경테 블랙 컬러 미디엄 사이즈",
    "embedding": [0.1, 0.2, 0.3, ...] # 1024차원 벡터
}

# 배치 벡터 삽입
batch_data = [
    {
        "id": [1, 2, 3],
        "product_id": [123, 124, 125], 
        "text_content": ["제품1 설명", "제품2 설명", "제품3 설명"],
        "embedding": [
            [0.1, 0.2, ...],  # 1024차원
            [0.3, 0.4, ...],  # 1024차원  
            [0.5, 0.6, ...]   # 1024차원
        ]
    }
]
```

## 📤 출력 데이터 형식

### 검색 결과
```python
search_result = {
    "hits": [
        {
            "id": 1,
            "distance": 0.95,      # 코사인 유사도 (높을수록 유사)
            "entity": {
                "id": 1,
                "product_id": 123,
                "text_content": "UNCOMMON 티타늄 안경테..."
            }
        },
        {
            "id": 2, 
            "distance": 0.88,
            "entity": {
                "id": 2,
                "product_id": 124,
                "text_content": "UNCOMMON 아세테이트 안경테..."
            }
        }
    ]
}
```

### 통계 정보
```python
stats = {
    "collection_name": "uncommon_products",
    "entity_count": 1500,
    "indexed_count": 1500,
    "dimension": 1024,
    "metric_type": "COSINE"
}
```

## 🔄 통신 방식

### 연결 프로토콜
- **프로토콜**: gRPC (HTTP/2 기반)
- **클라이언트**: pymilvus Python SDK
- **연결 풀**: 자동 관리
- **타임아웃**: 30초 기본값

### API 연동 방식
```python
from pymilvus import connections, Collection

# 연결 생성
connections.connect(
    alias="default",
    host="uncommon_rag-milvus",
    port="19530"
)

# 컬렉션 접근
collection = Collection("uncommon_products")

# 검색 실행
search_params = {
    "metric_type": "COSINE",
    "params": {"nprobe": 10}
}

results = collection.search(
    data=[query_vector],     # 검색할 벡터
    anns_field="embedding",  # 벡터 필드명
    param=search_params,     # 검색 파라미터
    limit=5,                 # 결과 개수
    output_fields=["product_id", "text_content"]
)
```

## 🔗 의존성

### 필수 의존성
- **Docker & Docker Compose**: 컨테이너 실행 환경
- **Milvus 2.3.3**: 벡터 데이터베이스 엔진
- **etcd**: 메타데이터 저장소
- **MinIO**: 객체 저장소

### 연관 서비스
- **Indexing Service**: 벡터 생성 및 저장
- **RAG API Service**: 벡터 검색 요청
- **PostgreSQL**: 원본 제품 데이터 연동

## 📈 성능 특성

### 검색 성능
- **지연시간**: < 50ms (1M 벡터 기준)
- **처리량**: 1000+ QPS
- **정확도**: 코사인 유사도 기반 정확한 유사성 측정

### 저장 용량
- **벡터당 용량**: ~4KB (1024 float32)
- **인덱스 오버헤드**: 원본 데이터의 ~20%
- **메모리 사용량**: 인덱스는 메모리에 로드

## 🔍 모니터링

### 상태 확인
```bash
# 컨테이너 상태
docker compose ps

# Milvus 로그
docker compose logs milvus-standalone

# 메트릭 확인 (Prometheus 형식)
curl http://localhost:9093/metrics
```

### Python SDK 모니터링
```python
from pymilvus import utility

# 컬렉션 통계
stats = utility.get_query_segment_info("uncommon_products")
print(f"Entity count: {stats}")

# 인덱스 상태
index_info = collection.describe_index()
print(f"Index info: {index_info}")
```

## ⚡ 최적화 팁

### 인덱스 최적화
- **nlist**: 벡터 수의 4√ 권장 (예: 10K 벡터 → nlist=100)
- **nprobe**: nlist의 5-10% 권장 (정확도 vs 속도 트레이드오프)

### 메모리 최적화
- **인덱스 로딩**: 자주 사용하는 컬렉션만 메모리에 로드
- **배치 처리**: 대량 삽입 시 배치 단위로 처리 (1000-10000개)

### 검색 최적화
- **필터링**: 필요한 필드만 output_fields에 지정
- **병렬 검색**: 여러 쿼리를 동시에 처리

## ⚠️ 주의사항
- **데이터 영속성**: Docker 볼륨 마운트로 데이터 보존
- **네트워크**: 내부 통신용 Docker 네트워크 사용
- **백업**: 컬렉션 데이터 정기 백업 권장
- **메모리**: 대용량 컬렉션 사용 시 충분한 RAM 필요