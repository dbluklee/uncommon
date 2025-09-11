# RAG API 서비스

## 📋 개요
Retrieval-Augmented Generation (RAG) 기반의 질의응답 API 서비스입니다. 사용자 질문을 벡터 검색으로 관련 제품 정보를 찾고, Ollama LLM을 통해 자연어 답변을 생성합니다. 실시간 스트리밍 응답을 지원합니다.

## 🎯 주요 기능
- **벡터 검색**: Milvus DB에서 유사도 기반 제품 검색
- **RAG 질의응답**: 검색된 정보를 바탕으로 LLM 답변 생성
- **스트리밍 응답**: Server-Sent Events로 실시간 답변 전송
- **멀티모달**: 텍스트 + 이미지 업로드 지원
- **검색 전용**: LLM 없이 순수 벡터 검색 기능

## 🚀 실행 방법

### 환경변수
```bash
RAG_API_PORT=8003                  # 외부 접근 포트
RAG_API_INTERNAL_PORT=8000        # 컨테이너 내부 포트
OLLAMA_HOST=112.148.37.41         # 외부 Ollama 서버
OLLAMA_PORT=1884                  # Ollama 포트
OLLAMA_MODEL=gemma3:27b-it-q4_K_M # LLM 모델명
EMBEDDING_MODEL=BAAI/bge-m3       # 임베딩 모델
USE_CUDA=true                     # CUDA 사용 여부
```

### 실행 명령
```bash
# 서비스 시작
cd rag-api
source ../.env.global
docker compose up -d

# 로컬 개발 실행
pip install -r requirements.txt
python main.py
```

### 접속 정보
- **API 서버**: `http://localhost:8003`
- **Swagger UI**: `http://localhost:8003/docs`

## 📡 API 엔드포인트

### 1. 서비스 상태 확인
```http
GET /
```

**응답 예시:**
```json
{
    "message": "RAG API Service is running",
    "ollama_host": "112.148.37.41:1884",
    "model": "gemma3:27b-it-q4_K_M",
    "embedding_model": "BAAI/bge-m3",
    "device": "cuda:0"
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
    "service": "rag-api",
    "ollama_connected": true,
    "milvus_connected": true,
    "model_loaded": true,
    "timestamp": "2024-01-10T10:30:00Z"
}
```

### 3. 벡터 검색 (LLM 없음)
```http
POST /search
Content-Type: application/json

{
    "query": "티타늄 안경테 추천해주세요",
    "top_k": 5
}
```

**응답 예시:**
```json
{
    "query": "티타늄 안경테 추천해주세요",
    "results": [
        {
            "product_id": 123,
            "score": 0.95,
            "content": "UNCOMMON Titanium Frame Black 프리미엄 티타늄 프레임...",
            "product_info": {
                "product_name": "UNCOMMON Titanium Frame",
                "color": "Black",
                "price": {"kr": "259,000원"},
                "material": {"kr": "티타늄, 아세테이트"}
            }
        }
    ],
    "processing_time": 0.15
}
```

### 4. RAG 채팅 (스트리밍)
```http
POST /chat
Content-Type: application/json
Accept: text/event-stream

{
    "query": "가벼운 안경테 추천해주세요",
    "stream": true,
    "top_k": 5
}
```

**스트리밍 응답 예시:**
```
data: {"type": "search_start", "message": "검색 중..."}

data: {"type": "search_results", "count": 3, "products": [...]}

data: {"type": "generation_start", "message": "답변 생성 중..."}

data: {"type": "token", "content": "안녕하세요! "}

data: {"type": "token", "content": "가벼운 안경테를 "}

data: {"type": "token", "content": "찾고 계시는군요. "}

data: {"type": "done", "message": "답변 완료"}
```

### 5. 멀티모달 채팅
```http
POST /chat/multimodal
Content-Type: multipart/form-data

query: "이 안경과 비슷한 제품 추천해주세요"
image: [이미지 파일]
stream: true
```

**응답**: `/chat`와 동일한 스트리밍 형태

### 6. 시스템 통계
```http
GET /stats
```

**응답 예시:**
```json
{
    "milvus_stats": {
        "collection": "uncommon_products",
        "entity_count": 150,
        "indexed_count": 150
    },
    "model_info": {
        "embedding_model": "BAAI/bge-m3",
        "llm_model": "gemma3:27b-it-q4_K_M",
        "device": "cuda:0"
    },
    "performance": {
        "avg_search_time": 0.12,
        "avg_generation_time": 2.3
    }
}
```

## 📊 입력/출력 데이터 형식

### 검색 요청
```json
{
    "query": "검은색 티타늄 안경테",
    "top_k": 5,
    "score_threshold": 0.7
}
```

### 채팅 요청
```json
{
    "query": "가벼운 안경테 추천해주세요",
    "stream": true,
    "top_k": 5,
    "context_window": 4000
}
```

### 검색 결과 형태
```python
search_results = {
    "query_embedding": [0.1, 0.2, ..., 0.9],  # 1024차원
    "retrieved_docs": [
        {
            "id": 1001,
            "product_id": 123,
            "score": 0.95,
            "text_content": "UNCOMMON Titanium Frame Black...",
            "metadata": {
                "product_name": "UNCOMMON Titanium Frame",
                "color": "Black",
                "material": {"kr": "티타늄, 아세테이트"}
            }
        }
    ]
}
```

### LLM 프롬프트 구성
```python
prompt_template = """
다음은 UNCOMMON 아이웢어 제품에 대한 정보입니다:

{retrieved_context}

사용자 질문: {user_query}

위 제품 정보를 바탕으로 친근하고 전문적인 톤으로 답변해주세요.
제품의 특징, 가격, 재질 등을 포함하여 구체적으로 추천해주세요.
"""
```

## 🔄 통신 방식

### HTTP REST API + SSE
```python
# 일반 JSON 응답
@app.post("/search")
async def search_products(request: SearchRequest):
    return JSONResponse(content=results)

# 스트리밍 응답  
@app.post("/chat")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        generate_streaming_response(request),
        media_type="text/event-stream"
    )
```

### Ollama LLM 통신
```python
import requests

def stream_ollama_response(prompt: str):
    response = requests.post(
        f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            yield json.loads(line)["response"]
```

### Milvus 벡터 검색
```python
from pymilvus import Collection

collection = Collection("uncommon_products")
search_params = {
    "metric_type": "COSINE",
    "params": {"nprobe": 10}
}

results = collection.search(
    data=[query_embedding],
    anns_field="embedding", 
    param=search_params,
    limit=top_k,
    output_fields=["product_id", "text_content"]
)
```

## 🔗 의존성

### 필수 의존성
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sentence-transformers==2.2.2
pymilvus==2.3.3
requests==2.31.0
sqlalchemy==2.0.23
asyncpg==0.29.0
python-multipart==0.0.6
torch==2.1.0
Pillow==10.1.0
```

### 외부 서비스 의존성
- **Ollama LLM 서버**: `112.148.37.41:1884`
  - 모델: `gemma3:27b-it-q4_K_M`
  - GPU 가속 외부 서버
- **Milvus 벡터DB**: 제품 벡터 검색
- **PostgreSQL DB**: 제품 상세 정보 조회

### 연관 서비스
- **Web App**: 사용자 인터페이스 제공
- **Indexing Service**: 벡터 데이터 생성

## 🧠 RAG 파이프라인

### 1. 쿼리 임베딩
```python
async def embed_query(query: str) -> List[float]:
    # BGE-M3 모델로 질문 벡터화
    embedding = embedding_model.encode([query], normalize_embeddings=True)
    return embedding[0].tolist()
```

### 2. 벡터 검색
```python
async def vector_search(query_embedding: List[float], top_k: int = 5):
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["product_id", "text_content"]
    )
    return results[0]
```

### 3. 컨텍스트 구성
```python
def build_context(search_results) -> str:
    context = ""
    for result in search_results:
        product_info = get_product_details(result.entity.get("product_id"))
        context += f"제품: {product_info['product_name']}\n"
        context += f"설명: {result.entity.get('text_content')}\n"
        context += f"가격: {product_info['price']['kr']}\n\n"
    return context
```

### 4. LLM 생성
```python
async def generate_response(prompt: str):
    async for chunk in ollama_stream_generate(prompt):
        yield {
            "type": "token",
            "content": chunk,
            "timestamp": datetime.now().isoformat()
        }
```

## 📈 성능 최적화

### 캐싱 전략
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_embedding(text: str) -> List[float]:
    return embedding_model.encode([text])[0].tolist()

# 검색 결과 캐싱 (Redis 권장, 현재는 메모리)
search_cache = {}
```

### 배치 처리
```python
# 여러 쿼리 동시 처리
async def batch_search(queries: List[str]):
    embeddings = embedding_model.encode(queries, batch_size=32)
    results = []
    for embedding in embeddings:
        result = await vector_search(embedding.tolist())
        results.append(result)
    return results
```

### 연결 풀링
```python
# Milvus 연결 풀
from pymilvus import connections
connections.connect(
    alias="default",
    host=MILVUS_HOST,
    port=MILVUS_INTERNAL_PORT,
    pool_size=10
)
```

## 📊 성능 메트릭

### 응답 시간
```python
performance_metrics = {
    "embedding_time": "50-100ms",
    "vector_search_time": "20-50ms", 
    "llm_first_token": "500-1000ms",
    "llm_streaming": "50-100 tokens/sec",
    "total_response": "2-5 seconds"
}
```

### 정확도 측정
```python
def calculate_search_relevance(query, results):
    relevance_scores = []
    for result in results:
        # 코사인 유사도 점수
        relevance_scores.append(result.distance)
    return {
        "avg_relevance": np.mean(relevance_scores),
        "max_relevance": max(relevance_scores),
        "results_count": len(results)
    }
```

## 🔍 모니터링 및 로깅

### 상세 로깅
```python
import logging

logger = logging.getLogger(__name__)

async def log_chat_session(query, results, response_time):
    logger.info(f"Chat Query: {query}")
    logger.info(f"Search Results: {len(results)} products found") 
    logger.info(f"Response Time: {response_time:.2f}s")
    logger.info(f"Top Relevance Score: {results[0].distance if results else 'N/A'}")
```

### 에러 처리
```python
try:
    search_results = await vector_search(query_embedding)
    llm_response = await generate_llm_response(context)
except Exception as e:
    logger.error(f"RAG Pipeline Error: {e}")
    yield {"type": "error", "message": "서비스 일시 장애. 잠시 후 다시 시도해주세요."}
```

## ⚠️ 주의사항
- **외부 의존성**: Ollama 서버 다운 시 RAG 기능 불가 (검색은 가능)
- **메모리 관리**: 임베딩 모델 GPU 메모리 사용량 주의
- **스트리밍 연결**: 클라이언트 연결 끊김 감지 및 처리
- **동시 요청**: 높은 동시성에서 Ollama 서버 부하 관리
- **토큰 제한**: LLM 컨텍스트 길이 초과 방지 (4000자 제한)