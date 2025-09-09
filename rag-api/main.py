"""
UNCOMMON RAG API Service
사용자 질의를 처리하고 관련 제품 정보를 기반으로 답변 생성
"""

import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import asyncio
import time
from datetime import datetime

# 프로젝트 모듈 임포트
from embedding_generator import EmbeddingGenerator
from vector_search import VectorSearcher
from llm_client import LLMClient

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="UNCOMMON RAG API Service",
    description="벡터 검색 기반 제품 정보 질의응답 서비스",
    version="1.0.0"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 인스턴스
embedding_generator = None
vector_searcher = None
llm_client = None

# JWT authentication removed for MVP

# 시스템 프롬프트 (메모리에 저장, 실제로는 DB나 파일에 저장)
SYSTEM_PROMPT = """다음은 UNCOMMON 안경 제품에 대한 정보를 기반으로 사용자의 질문에 답변하는 AI 어시스턴트입니다.

사용자 질문: {query}

관련 제품 정보:
{context}

위 정보를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공해주세요. 
- 제품명, 가격, 특징을 구체적으로 언급해주세요
- 한국어로 친근하게 답변해주세요
- 정보가 불충분하다면 그 사실을 명시해주세요"""

# 요청/응답 모델
class ChatRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    stream: Optional[bool] = True
    temperature: Optional[float] = 0.7
    include_images: Optional[bool] = False
    include_debug: Optional[bool] = False

class MultiModalChatRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    stream: Optional[bool] = True
    temperature: Optional[float] = 0.7
    include_debug: Optional[bool] = False

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    query_embedding_dim: int

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    query: str
    total_results: int

# 관리자 모델들
class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    token: str
    user: str
    expires_at: datetime

class SystemPromptRequest(BaseModel):
    prompt: str

class SystemPromptResponse(BaseModel):
    prompt: str
    updated_at: datetime

class DocumentCreateRequest(BaseModel):
    title: str
    content: str
    category: str = "manual"

class DocumentResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    created_at: datetime
    vector_count: int

# JWT authentication functions removed for MVP

@app.on_event("startup")
async def startup_event():
    """서비스 시작 시 초기화"""
    global embedding_generator, vector_searcher, llm_client
    
    try:
        logger.info("🚀 UNCOMMON RAG API 서비스 시작")
        
        # 임베딩 생성기 초기화
        logger.info("📥 임베딩 모델 로딩 중...")
        embedding_generator = EmbeddingGenerator()
        logger.info("✅ 임베딩 모델 로딩 완료")
        
        # 벡터 검색기 초기화
        logger.info("🔗 Milvus 벡터 검색기 초기화 중...")
        vector_searcher = VectorSearcher(embedding_generator)
        logger.info("✅ Milvus 벡터 검색기 초기화 완료")
        
        # LLM 클라이언트 초기화
        logger.info("🤖 Ollama LLM 클라이언트 초기화 중...")
        llm_client = LLMClient()
        logger.info("✅ Ollama LLM 클라이언트 초기화 완료")
        
        logger.info("🎉 모든 모듈 초기화 완료!")
        
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {str(e)}")
        raise

@app.get("/")
async def root():
    """서비스 상태 확인"""
    return {
        "service": "UNCOMMON RAG API Service",
        "status": "running",
        "version": "1.0.0",
        "embedding_model": os.environ["EMBEDDING_MODEL"],
        "llm_model": os.environ["OLLAMA_MODEL"],
        "vector_store": "Milvus"
    }

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy"}

@app.post("/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """
    제품 벡터 검색 (LLM 없이 검색만)
    """
    try:
        logger.info(f"🔍 검색 요청: {request.query}")
        
        # 벡터 검색 수행
        search_results = await vector_searcher.search(
            query=request.query,
            top_k=request.top_k
        )
        
        # 결과 포맷팅
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "content": result.get("content", ""),
                "product_id": result.get("product_id", 0),
                "product_name": result.get("product_name", ""),
                "chunk_type": result.get("chunk_type", ""),
                "source": result.get("source", ""),
                "score": result.get("score", 0.0)
            })
        
        logger.info(f"✅ {len(formatted_results)}개 결과 반환")
        
        return SearchResponse(
            results=formatted_results,
            query=request.query,
            total_results=len(formatted_results)
        )
        
    except Exception as e:
        logger.error(f"❌ 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    RAG 기반 질의응답 (스트리밍 지원)
    """
    try:
        start_time = time.time()
        logger.info(f"💬 채팅 요청: {request.query}")
        
        # 1. 벡터 검색 수행
        search_start = time.time()
        search_results = await vector_searcher.search(
            query=request.query,
            top_k=request.top_k
        )
        search_end = time.time()
        logger.info(f"⏱️ 벡터 검색 완료: {search_end - search_start:.2f}초")
        
        if not search_results:
            logger.warning("⚠️ 관련 제품을 찾을 수 없습니다")
            return ChatResponse(
                answer="죄송합니다. 관련된 제품 정보를 찾을 수 없습니다.",
                sources=[],
                query_embedding_dim=1024
            )
        
        # 2. 컨텍스트 구성
        context_start = time.time()
        context = _build_context(search_results)
        context_end = time.time()
        logger.info(f"⏱️ 컨텍스트 구성 완료: {context_end - context_start:.2f}초")
        
        # 3. LLM 응답 생성
        if request.stream:
            # 스트리밍 응답
            logger.info("📡 스트리밍 응답 시작")
            return StreamingResponse(
                _stream_response(request.query, context, search_results, request.temperature, request),
                media_type="text/event-stream"
            )
        else:
            # 일반 응답
            llm_start = time.time()
            logger.info("🤖 LLM 응답 생성 시작...")
            answer = await llm_client.generate(
                query=request.query,
                context=context,
                temperature=request.temperature
            )
            llm_end = time.time()
            total_end = time.time()
            
            logger.info(f"⏱️ LLM 응답 생성 완료: {llm_end - llm_start:.2f}초")
            logger.info(f"⏱️ 전체 처리 시간: {total_end - start_time:.2f}초")
            
            response_data = ChatResponse(
                answer=answer,
                sources=_format_sources(search_results),
                query_embedding_dim=1024
            )
            
            # 디버깅 정보가 요청된 경우 추가
            if request.include_debug:
                debug_info = _build_debug_info(request.query, search_results, context, request)
                # ChatResponse 모델에 debug_info 필드를 추가하거나, dict로 반환
                return {
                    "answer": answer,
                    "sources": _format_sources(search_results),
                    "query_embedding_dim": 1024,
                    "debug_info": debug_info
                }
            
            return response_data
            
    except Exception as e:
        logger.error(f"❌ 채팅 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/multimodal")
async def multimodal_chat(
    query: str = Form(...),
    top_k: Optional[int] = Form(5),
    stream: Optional[bool] = Form(True), 
    temperature: Optional[float] = Form(0.7),
    include_debug: Optional[bool] = Form(False),
    image: Optional[UploadFile] = File(None)
):
    """
    멀티모달 RAG 기반 질의응답 (이미지 + 텍스트)
    """
    try:
        start_time = time.time()
        logger.info(f"🖼️ 멀티모달 채팅 요청: {query}")
        
        # 이미지 처리
        image_data = None
        if image and image.size > 0:
            # 이미지 크기 제한 (10MB)
            if image.size > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="이미지 크기가 10MB를 초과합니다")
            
            # 지원되는 이미지 형식 확인
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_types:
                raise HTTPException(status_code=400, detail="지원되지 않는 이미지 형식입니다. (JPEG, PNG, GIF, WebP 지원)")
            
            image_data = await image.read()
            logger.info(f"📷 이미지 업로드됨: {image.filename}, 크기: {len(image_data)} bytes, 타입: {image.content_type}")
        
        # 1. 벡터 검색 수행
        search_start = time.time()
        search_results = await vector_searcher.search(
            query=query,
            top_k=top_k
        )
        search_end = time.time()
        logger.info(f"⏱️ 벡터 검색 완료: {search_end - search_start:.2f}초")
        
        if not search_results:
            logger.warning("⚠️ 관련 제품을 찾을 수 없습니다")
            return ChatResponse(
                answer="죄송합니다. 관련된 제품 정보를 찾을 수 없습니다.",
                sources=[],
                query_embedding_dim=1024
            )
        
        # 2. 컨텍스트 구성
        context_start = time.time()
        context = _build_context(search_results)
        context_end = time.time()
        logger.info(f"⏱️ 컨텍스트 구성 완료: {context_end - context_start:.2f}초")
        
        # 3. LLM 응답 생성 (이미지 포함)
        if stream:
            # 스트리밍 응답
            logger.info(f"📡 {'멀티모달 ' if image_data else ''}스트리밍 응답 시작")
            return StreamingResponse(
                _stream_multimodal_response(query, context, search_results, temperature, image_data, include_debug),
                media_type="text/event-stream"
            )
        else:
            # 일반 응답
            llm_start = time.time()
            logger.info(f"🤖 {'멀티모달 ' if image_data else ''}LLM 응답 생성 시작...")
            answer = await llm_client.generate(
                query=query,
                context=context,
                temperature=temperature,
                image_data=image_data
            )
            llm_end = time.time()
            total_end = time.time()
            
            logger.info(f"⏱️ LLM 응답 생성 완료: {llm_end - llm_start:.2f}초")
            logger.info(f"⏱️ 전체 처리 시간: {total_end - start_time:.2f}초")
            
            response_data = ChatResponse(
                answer=answer,
                sources=_format_sources(search_results),
                query_embedding_dim=1024
            )
            
            # 디버깅 정보가 요청된 경우 추가
            if include_debug:
                debug_info = _build_debug_info(query, search_results, context, ChatRequest(
                    query=query, top_k=top_k, temperature=temperature, stream=stream, include_debug=include_debug
                ))
                return {
                    "answer": answer,
                    "sources": _format_sources(search_results),
                    "query_embedding_dim": 1024,
                    "debug_info": debug_info,
                    "has_image": image_data is not None
                }
            
            return response_data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 멀티모달 채팅 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def _build_context(search_results: List[Dict]) -> str:
    """검색 결과로부터 컨텍스트 구성"""
    context_parts = []
    max_length = int(os.environ["MAX_CONTEXT_LENGTH"])
    current_length = 0
    
    for i, result in enumerate(search_results, 1):
        content = result.get("content", "")
        product_name = result.get("product_name", "")
        chunk_type = result.get("chunk_type", "")
        
        # 제품 정보 포함한 컨텍스트 생성
        context_item = f"[제품정보 {i}]\n"
        if product_name:
            context_item += f"제품명: {product_name}\n"
        if chunk_type:
            context_item += f"정보 유형: {chunk_type}\n"
        context_item += f"{content}\n"
        
        # 길이 체크
        if current_length + len(context_item) > max_length:
            break
            
        context_parts.append(context_item)
        current_length += len(context_item)
    
    return "\n".join(context_parts)

def _format_sources(search_results: List[Dict]) -> List[Dict]:
    """검색 결과를 소스 형식으로 변환"""
    sources = []
    for result in search_results:
        sources.append({
            "product_name": result.get("product_name", "Unknown"),
            "product_id": result.get("product_id"),
            "chunk_type": result.get("chunk_type"),
            "score": result.get("score", 0.0)
        })
    return sources

def _build_debug_info(query: str, search_results: List[Dict], context: str, request: ChatRequest) -> Dict[str, Any]:
    """디버깅 정보 생성"""
    return {
        "query": query,
        "search_results": [
            {
                "product_name": result.get("product_name", "Unknown"),
                "chunk_type": result.get("chunk_type", "unknown"),
                "content": result.get("content", "")[:500],  # 처음 500자만
                "score": result.get("score", 0.0),
                "product_id": result.get("product_id"),
                "source": result.get("source", "")
            }
            for result in search_results
        ],
        "prompt": SYSTEM_PROMPT.format(query=query, context=context),
        "settings": {
            "top_k": request.top_k,
            "temperature": request.temperature,
            "embedding_model": os.environ["EMBEDDING_MODEL"],
            "llm_model": os.environ["OLLAMA_MODEL"],
            "stream": request.stream,
            "max_context_length": int(os.environ["MAX_CONTEXT_LENGTH"])
        }
    }

async def _stream_response(query: str, context: str, search_results: List[Dict], temperature: float, request: ChatRequest = None):
    """스트리밍 응답 생성"""
    try:
        # 디버깅 정보 준비
        debug_info = None
        if request and request.include_debug:
            debug_info = _build_debug_info(query, search_results, context, request)
        
        # 스트리밍 시작 이벤트 (디버깅 정보 포함)
        start_data = {
            'type': 'start', 
            'sources': _format_sources(search_results)
        }
        if debug_info:
            start_data['debug_info'] = debug_info
        
        yield f"data: {json.dumps(start_data)}\n\n"
        
        # LLM 스트리밍 응답
        async for chunk in llm_client.stream_generate(query, context, temperature):
            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)  # 백프레셔 제어
        
        # 스트리밍 종료 이벤트
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
        
    except Exception as e:
        logger.error(f"스트리밍 오류: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

async def _stream_multimodal_response(query: str, context: str, search_results: List[Dict], temperature: float, image_data: Optional[bytes] = None, include_debug: bool = False):
    """멀티모달 스트리밍 응답 생성"""
    try:
        # 디버깅 정보 준비
        debug_info = None
        if include_debug:
            debug_info = _build_debug_info(query, search_results, context, ChatRequest(
                query=query, temperature=temperature, stream=True, include_debug=include_debug
            ))
        
        # 스트리밍 시작 이벤트 (디버깅 정보 포함)
        start_data = {
            'type': 'start', 
            'sources': _format_sources(search_results),
            'has_image': image_data is not None
        }
        if debug_info:
            start_data['debug_info'] = debug_info
        
        yield f"data: {json.dumps(start_data)}\n\n"
        
        # LLM 스트리밍 응답 (이미지 포함)
        async for chunk in llm_client.stream_generate(query, context, temperature, image_data):
            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)  # 백프레셔 제어
        
        # 스트리밍 종료 이벤트
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
        
    except Exception as e:
        logger.error(f"멀티모달 스트리밍 오류: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

@app.get("/stats")
async def get_stats():
    """시스템 통계 정보"""
    try:
        stats = await vector_searcher.get_collection_stats()
        return {
            "collection_name": os.environ["COLLECTION_NAME"],
            "total_vectors": stats.get("row_count", 0),
            "embedding_dim": int(os.environ["DIMENSION"]),
            "metric_type": os.environ["METRIC_TYPE"]
        }
    except Exception as e:
        logger.error(f"통계 조회 실패: {str(e)}")
        return {"error": str(e)}

# Admin endpoints removed for MVP

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ["RAG_API_INTERNAL_PORT"])
    uvicorn.run(app, host="0.0.0.0", port=port)