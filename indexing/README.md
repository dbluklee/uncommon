# Indexing 서비스

## 📋 개요
PostgreSQL에 저장된 제품 데이터를 BGE-M3 임베딩 모델로 벡터화하여 Milvus 벡터 데이터베이스에 저장하는 인덱싱 서비스입니다. CPU와 GPU를 자동으로 감지하여 최적의 성능을 제공합니다.

## 🎯 주요 기능
- **텍스트 임베딩**: BGE-M3 모델을 사용한 1024차원 벡터 생성
- **텍스트 청킹**: 제품 정보를 검색에 최적화된 청크로 분할
- **벡터 저장**: Milvus 데이터베이스에 임베딩 벡터 저장
- **배치 처리**: 대량 제품 데이터의 효율적인 일괄 처리
- **CUDA 가속**: GPU 사용 시 임베딩 성능 대폭 향상

## 🚀 실행 방법

### 환경변수
```bash
INDEXING_PORT=8002                  # 외부 접근 포트
INDEXING_INTERNAL_PORT=8000        # 컨테이너 내부 포트
EMBEDDING_MODEL=BAAI/bge-m3        # 임베딩 모델
USE_CUDA=true                      # CUDA 사용 여부
CUDA_DEVICE=0                      # GPU 디바이스 번호
DIMENSION=1024                     # 벡터 차원
MAX_CONTEXT_LENGTH=4000           # 최대 텍스트 길이
```

### 실행 명령
```bash
# 서비스 시작
cd indexing
source ../.env.global
docker compose up -d

# 로컬 개발 실행 (CUDA 환경)
pip install -r requirements.txt
python main.py
```

### 접속 정보
- **API 서버**: `http://localhost:8002`
- **Swagger UI**: `http://localhost:8002/docs`

## 📡 API 엔드포인트

### 1. 서비스 상태 확인
```http
GET /
```

**응답 예시:**
```json
{
    "message": "Indexing Service is running",
    "embedding_model": "BAAI/bge-m3",
    "device": "cuda:0",
    "dimension": 1024
}
```

### 2. 헬스체크
```http
GET /health
```

**응답 예시:**
```json
{
    "status": "healthy",
    "service": "indexing",
    "model_loaded": true,
    "milvus_connected": true,
    "timestamp": "2024-01-10T10:30:00Z"
}
```

### 3. 전체 제품 인덱싱 (백그라운드)
```http
POST /index/products
```

**응답 예시:**
```json
{
    "message": "인덱싱 작업이 백그라운드에서 시작되었습니다",
    "total_products": 150,
    "status": "started"
}
```

### 4. 인덱싱 통계 조회
```http
GET /index/stats
```

**응답 예시:**
```json
{
    "total_products": 150,
    "indexed_products": 120,
    "pending_products": 30,
    "collection_info": {
        "name": "uncommon_products",
        "dimension": 1024,
        "metric_type": "COSINE",
        "entity_count": 120
    }
}
```

### 5. 개별 제품 인덱싱
```http
POST /index/products/{product_id}
```

**응답 예시:**
```json
{
    "product_id": 123,
    "chunks_created": 3,
    "vectors_inserted": 3,
    "status": "completed"
}
```

### 6. 제품 인덱스 삭제
```http
DELETE /index/products/{product_id}
```

**응답 예시:**
```json
{
    "product_id": 123,
    "vectors_deleted": 3,
    "status": "deleted"
}
```

## 📊 입력/출력 데이터 형식

### 입력 데이터 (PostgreSQL에서 조회)
```python
product_data = {
    "id": 123,
    "product_name": "UNCOMMON Titanium Frame",
    "color": "Black", 
    "price": {"global": "$199.00", "kr": "259,000원"},
    "description": {"global": "Premium titanium frame", "kr": "프리미엄 티타늄 프레임"},
    "material": {"global": "Titanium, Acetate", "kr": "티타늄, 아세테이트"},
    "size": {"global": "Medium (52-18-145)", "kr": "미디엄 (52-18-145)"}
}
```

### 텍스트 청킹 결과
```python
chunks = [
    {
        "chunk_id": 1,
        "text": "UNCOMMON Titanium Frame Black 프리미엄 티타늄 프레임 고급 아이웨어",
        "chunk_type": "product_name_description"
    },
    {
        "chunk_id": 2, 
        "text": "재질: 티타늄, 아세테이트 고품질 소재 경량 내구성",
        "chunk_type": "material_features"
    },
    {
        "chunk_id": 3,
        "text": "사이즈: 미디엄 (52-18-145) 가격: $199.00 259,000원",
        "chunk_type": "size_price"
    }
]
```

### 벡터 생성 결과
```python
embeddings = [
    {
        "id": 1001,
        "product_id": 123,
        "text_content": "UNCOMMON Titanium Frame Black 프리미엄 티타늄 프레임...",
        "embedding": [0.123, -0.456, 0.789, ..., 0.321]  # 1024차원 벡터
    },
    {
        "id": 1002,
        "product_id": 123, 
        "text_content": "재질: 티타늄, 아세테이트 고품질 소재...",
        "embedding": [0.234, -0.567, 0.890, ..., 0.432]  # 1024차원 벡터
    }
]
```

## 🔄 통신 방식

### HTTP REST API
- **프로토콜**: HTTP/1.1
- **포맷**: JSON
- **인코딩**: UTF-8
- **비동기 처리**: FastAPI + asyncio

### 데이터베이스 연동
```python
# PostgreSQL 연결
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine(
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Milvus 연결
from pymilvus import connections, Collection
connections.connect(
    host=MILVUS_HOST,
    port=MILVUS_INTERNAL_PORT
)
```

### 임베딩 모델 로딩
```python
from sentence_transformers import SentenceTransformer
import torch

# CUDA 자동 감지
device = "cuda" if torch.cuda.is_available() and USE_CUDA else "cpu"
model = SentenceTransformer(EMBEDDING_MODEL, device=device)
```

## 🔗 의존성

### 필수 의존성
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
sentence-transformers==2.2.2
pymilvus==2.3.3
torch==2.1.0
transformers==4.35.2
numpy==1.24.3
```

### CUDA 의존성 (GPU 사용 시)
```txt
torch==2.1.0+cu121
torchvision==0.16.0+cu121
torchaudio==2.1.0+cu121
```

### 시스템 의존성
- **Python 3.11+**
- **CUDA 12.1** (GPU 사용 시)
- **PostgreSQL 데이터베이스**: 제품 데이터 조회
- **Milvus 벡터DB**: 벡터 저장

### 연관 서비스
- **PostgreSQL DB**: 원본 제품 데이터 소스
- **Milvus DB**: 벡터 데이터 저장소
- **Scraper Service**: 새 제품 데이터 수집 시 인덱싱 트리거

## 🧠 임베딩 모델 (BGE-M3)

### 모델 특징
```python
model_info = {
    "name": "BAAI/bge-m3",
    "type": "multilingual",
    "dimension": 1024,
    "max_length": 8192,
    "languages": ["en", "ko", "zh", "ja", ...],
    "performance": "SOTA on multilingual retrieval tasks"
}
```

### 벡터 생성 과정
```python
def generate_embeddings(texts: List[str]) -> List[List[float]]:
    # 배치 처리로 효율성 향상
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True  # 코사인 유사도 최적화
    )
    return embeddings.tolist()
```

### GPU 메모리 관리
```python
# GPU 메모리 정리
if torch.cuda.is_available():
    torch.cuda.empty_cache()
    
# 배치 크기 동적 조정
max_batch_size = 32 if device == "cuda" else 8
```

## 📝 텍스트 청킹 전략

### 제품별 청킹 로직
```python
def create_product_chunks(product: dict) -> List[dict]:
    chunks = []
    
    # 청크 1: 제품명 + 기본 정보
    chunk1 = f"{product['product_name']} {product.get('color', '')} "
    chunk1 += f"{product['description'].get('kr', '')} {product['description'].get('global', '')}"
    chunks.append({"text": chunk1, "type": "product_basic"})
    
    # 청크 2: 재질 + 특징
    material_kr = product['material'].get('kr', '')
    material_global = product['material'].get('global', '')
    chunk2 = f"재질: {material_kr} {material_global} 고품질 소재 내구성"
    chunks.append({"text": chunk2, "type": "material_features"})
    
    # 청크 3: 사이즈 + 가격
    size_info = f"사이즈: {product['size'].get('kr', '')} {product['size'].get('global', '')}"
    price_info = f"가격: {product['price'].get('global', '')} {product['price'].get('kr', '')}"
    chunk3 = f"{size_info} {price_info}"
    chunks.append({"text": chunk3, "type": "size_price"})
    
    return chunks
```

### 청킹 최적화
- **최대 길이**: 4000자 (모델 컨텍스트 고려)
- **중복 제거**: 동일한 청크 내용 중복 방지
- **의미 보존**: 문맥상 의미가 끊어지지 않도록 분할

## 📈 성능 모니터링

### 처리 성능
```python
performance_metrics = {
    "cpu_processing": "10-15 products/minute",
    "gpu_processing": "50-100 products/minute",
    "batch_size_optimal": 32,
    "memory_usage": "2-4GB (GPU), 500MB (CPU)"
}
```

### 에러 처리
```python
try:
    embeddings = model.encode(texts)
    insert_to_milvus(embeddings)
    update_product_indexed_status(product_id, True)
except Exception as e:
    logger.error(f"인덱싱 실패 (Product ID: {product_id}): {e}")
    update_product_indexed_status(product_id, False)
    raise
```

### 로깅
```python
logger.info(f"인덱싱 시작: {total_products}개 제품")
logger.info(f"벡터 생성 완료: {len(embeddings)}개")
logger.info(f"Milvus 저장 완료: {insert_count}개")
logger.info(f"처리 시간: {processing_time:.2f}초")
```

## ⚠️ 주의사항
- **GPU 메모리**: 대량 처리 시 GPU 메모리 부족 주의
- **모델 로딩**: 초기 모델 로딩에 시간 소요 (1-2분)
- **배치 처리**: 너무 큰 배치는 메모리 오버플로우 위험
- **중복 인덱싱**: 이미 인덱싱된 제품 재처리 방지 로직 필요
- **네트워크**: Milvus 연결 끊김 시 재연결 로직 구현