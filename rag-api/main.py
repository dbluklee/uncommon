# RAG LLM 시스템의 메인 API 서비스 - 사용자 질의에 대한 인텔리전트 답변 제공
# 목적: 벡터 검색 + LLM을 활용한 Retrieval-Augmented Generation 기반 질의응답 시스템
# 관련 함수: chat (메인 RAG), search (벡터 검색), _stream_rag_response (실시간 스트리밍)
# 주요 기능: Conditional RAG, 멀티모달 지원, 실시간 스트리밍, 디버깅
"""
UNCOMMON RAG API Service - BGE-M3 벡터 검색 + Ollama LLM 기반 제품 정보 질의응답
주요 특징: Router LLM으로 RAG 사용 여부 결정, 실시간 스트리밍 응답, 멀티모달 지원
"""

import os
import logging  # API 요청 및 오류 로깅
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Form, File, UploadFile
from fastapi.responses import StreamingResponse  # 실시간 스트리밍 응답
from fastapi.middleware.cors import CORSMiddleware  # 크로스 도메인 요청 처리
from pydantic import BaseModel  # API 데이터 모델 정의
from dotenv import load_dotenv  # 환경변수 로드
import json
import asyncio  # 비동기 스트리밍 처리
import time
from datetime import datetime

# RAG 시스템 핵심 모듈 임포트 - 각각 특화된 기능 담당
from embedding_generator import EmbeddingGenerator  # BGE-M3 임베딩 모델 관리
from services.vector_search_service import VectorSearchService  # Milvus 벡터 검색 서비스
from llm_client import LLMClient  # Ollama LLM 클라이언트
from router_llm_client import RouterLLMClient  # RAG 사용 여부 결정 라우터

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 초기화 - RAG 기반 질의응답 API 서비스
app = FastAPI(
    title="UNCOMMON RAG API Service",
    description="벡터 검색 기반 제품 정보 질의응답 서비스",
    version="1.0.0"
)

# CORS 설정 - 웹 브라우저에서 API 접근 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP에서는 모든 도메인 허용 (프로덕션에서는 제한 필요)
    allow_credentials=True,  # 쿠키 및 인증 헤더 허용
    allow_methods=["*"],  # 모든 HTTP 메소드 허용 (GET, POST, etc.)
    allow_headers=["*"],  # 모든 HTTP 헤더 허용
)

# 전역 인스턴스
embedding_generator = None
vector_search_service = None
llm_client = None
router_llm_client = None

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
    global embedding_generator, vector_search_service, llm_client, router_llm_client
    
    try:
        logger.info("🚀 UNCOMMON RAG API 서비스 시작")
        
        # Router LLM 클라이언트 초기화 (가장 먼저)
        logger.info("🎯 Router LLM 클라이언트 초기화 중...")
        router_llm_client = RouterLLMClient()
        logger.info("✅ Router LLM 클라이언트 초기화 완료")
        
        # 임베딩 생성기 초기화
        logger.info("📥 임베딩 모델 로딩 중...")
        embedding_generator = EmbeddingGenerator()
        logger.info("✅ 임베딩 모델 로딩 완료")
        
        # 벡터 검색 서비스 초기화
        logger.info("🔗 벡터 검색 서비스 초기화 중...")
        vector_search_service = VectorSearchService(embedding_generator)
        logger.info("✅ 벡터 검색 서비스 초기화 완료")
        
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
        search_results = await vector_search_service.search_similar_documents(
            query=request.query,
            top_k=request.top_k
        )
        
        # 새로운 서비스에서는 이미 올바른 형태로 반환되므로 포맷팅 불필요
        logger.info(f"✅ {len(search_results)}개 결과 반환")
        
        return SearchResponse(
            results=search_results,
            query=request.query,
            total_results=len(search_results)
        )
        
    except Exception as e:
        logger.error(f"❌ 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Conditional RAG 기반 질의응답 (스트리밍 지원)
    """
    try:
        start_time = time.time()
        logger.info(f"💬 채팅 요청: {request.query}")
        
        # 1. Router로 RAG 필요성 판단
        router_start = time.time()
        needs_rag = await router_llm_client.should_use_rag(request.query)
        router_end = time.time()
        logger.info(f"⏱️ Router 판단 완료: {router_end - router_start:.2f}초")
        
        if not needs_rag:
            # RAG 없이 직접 응답
            logger.info("🎯 직접 응답 모드 (RAG 미사용)")
            
            if request.stream:
                # 스트리밍 직접 응답
                logger.info("📡 직접 스트리밍 응답 시작")
                return StreamingResponse(
                    _stream_direct_response(request.query, request.temperature, request),
                    media_type="text/event-stream"
                )
            else:
                # 일반 직접 응답
                llm_start = time.time()
                answer = await router_llm_client.generate_direct_response(
                    query=request.query,
                    temperature=request.temperature
                )
                llm_end = time.time()
                total_end = time.time()
                
                logger.info(f"⏱️ 직접 응답 생성 완료: {llm_end - llm_start:.2f}초")
                logger.info(f"⏱️ 전체 처리 시간: {total_end - start_time:.2f}초")
                
                response_data = ChatResponse(
                    answer=answer,
                    sources=[],  # 직접 응답은 소스 없음
                    query_embedding_dim=1024
                )
                
                # 디버깅 정보가 요청된 경우 추가
                if request.include_debug:
                    debug_info = {
                        "query": request.query,
                        "router_decision": "직접 응답 (RAG 미사용)",
                        "search_results": [],
                        "prompt": f"직접 응답 프롬프트로 생성: {request.query}",
                        "settings": {
                            "top_k": request.top_k,
                            "temperature": request.temperature,
                            "router_model": os.environ["ROUTER_LLM_MODEL"],
                            "stream": request.stream
                        }
                    }
                    return {
                        "answer": answer,
                        "sources": [],
                        "query_embedding_dim": 1024,
                        "debug_info": debug_info
                    }
                
                return response_data
        else:
            # RAG 사용
            logger.info("🎯 RAG 모드 (벡터 검색 + 컨텍스트 기반 응답)")
            
            # 2. 벡터 검색 수행
            search_start = time.time()
            search_results = await vector_search_service.search_similar_documents(
                query=request.query,
                top_k=request.top_k
            )
            search_end = time.time()
            logger.info(f"⏱️ 벡터 검색 완료: {search_end - search_start:.2f}초")
            
            # 3. 컨텍스트 구성
            context_start = time.time()
            if not search_results:
                logger.warning("⚠️ 관련 제품을 찾을 수 없습니다")
                # RAG 필요하지만 데이터 없으면 컨텍스트에 "정보 없음"을 명시
                context = "검색 결과: 요청하신 제품에 대한 정보를 데이터베이스에서 찾을 수 없습니다."
                search_results = []  # 빈 결과 리스트
            else:
                context = _build_context(search_results)
            context_end = time.time()
            logger.info(f"⏱️ 컨텍스트 구성 완료: {context_end - context_start:.2f}초")
            
            # 4. LLM 응답 생성 (RAG)
            if request.stream:
                # 스트리밍 응답
                logger.info("📡 RAG 스트리밍 응답 시작")
                return StreamingResponse(
                    _stream_rag_response(request.query, context, search_results, request.temperature, request),
                    media_type="text/event-stream"
                )
            else:
                # 일반 응답
                llm_start = time.time()
                logger.info("🤖 RAG LLM 응답 생성 시작...")
                answer = await llm_client.generate(
                    query=request.query,
                    context=context,
                    temperature=request.temperature
                )
                llm_end = time.time()
                total_end = time.time()
                
                logger.info(f"⏱️ RAG LLM 응답 생성 완료: {llm_end - llm_start:.2f}초")
                logger.info(f"⏱️ 전체 처리 시간: {total_end - start_time:.2f}초")
                
                response_data = ChatResponse(
                    answer=answer,
                    sources=_format_sources(search_results),
                    query_embedding_dim=1024
                )
                
                # 디버깅 정보가 요청된 경우 추가
                if request.include_debug:
                    debug_info = _build_debug_info(request.query, search_results, context, request)
                    debug_info["router_decision"] = "RAG 사용 (제품 정보 필요)"
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
        search_results = await vector_search_service.search_similar_documents(
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

async def _stream_direct_response(query: str, temperature: float, request: ChatRequest = None):
    """직접 응답 스트리밍"""
    try:
        # 디버깅 정보 준비
        debug_info = None
        if request and request.include_debug:
            debug_info = {
                "query": query,
                "router_decision": "직접 응답 (RAG 미사용)",
                "search_results": [],
                "prompt": f"직접 응답 프롬프트로 생성: {query}",
                "settings": {
                    "top_k": request.top_k,
                    "temperature": temperature,
                    "router_model": os.environ["ROUTER_LLM_MODEL"],
                    "stream": request.stream
                }
            }
        
        # 스트리밍 시작 이벤트
        start_data = {
            'type': 'start', 
            'sources': []
        }
        if debug_info:
            start_data['debug_info'] = debug_info
        
        yield f"data: {json.dumps(start_data)}\n\n"
        
        # Router LLM 스트리밍 응답
        async for chunk in router_llm_client.stream_direct_response(query, temperature):
            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            await asyncio.sleep(0.01)
        
        # 스트리밍 종료 이벤트
        yield f"data: {json.dumps({'type': 'end'})}\n\n"
        
    except Exception as e:
        logger.error(f"직접 응답 스트리밍 오류: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

async def _stream_rag_response(query: str, context: str, search_results: List[Dict], temperature: float, request: ChatRequest = None):
    """RAG 스트리밍 응답 생성"""
    try:
        # 디버깅 정보 준비
        debug_info = None
        if request and request.include_debug:
            debug_info = _build_debug_info(query, search_results, context, request)
            debug_info["router_decision"] = "RAG 사용 (제품 정보 필요)"
        
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
        logger.error(f"RAG 스트리밍 오류: {str(e)}")
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
        stats = await vector_search_service.get_service_stats()
        return {
            "collection_name": os.environ["COLLECTION_NAME"],
            "total_vectors": stats.get("vector_store", {}).get("row_count", 0),
            "embedding_dim": int(os.environ["DIMENSION"]),
            "metric_type": os.environ["METRIC_TYPE"]
        }
    except Exception as e:
        logger.error(f"통계 조회 실패: {str(e)}")
        return {"error": str(e)}

# Admin endpoints for management dashboard
@app.get("/admin/stats")
async def get_admin_stats():
    """관리자 대시보드 통계"""
    try:
        stats = await vector_search_service.get_service_stats()
        return {
            "total_documents": 0,  # MVP에서는 제품 기반이므로 0
            "total_vectors": stats.get("vector_store", {}).get("row_count", 0),
            "last_update": "실시간"
        }
    except Exception as e:
        logger.error(f"관리자 통계 조회 실패: {str(e)}")
        return {
            "total_documents": 0,
            "total_vectors": 0,
            "last_update": "오류"
        }

@app.get("/admin/prompt")
async def get_system_prompt():
    """현재 시스템 프롬프트 조회"""
    return {"prompt": SYSTEM_PROMPT}

@app.post("/admin/prompt")
async def update_system_prompt(request: SystemPromptRequest):
    """시스템 프롬프트 업데이트"""
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = request.prompt
    logger.info("시스템 프롬프트가 업데이트됨")
    return {
        "prompt": SYSTEM_PROMPT,
        "updated_at": datetime.now()
    }

@app.get("/admin/documents")
async def get_documents():
    """문서 목록 조회 (MVP에서는 제품 데이터 반환)"""
    try:
        # PostgreSQL에서 제품 데이터 조회
        import psycopg2
        import json
        
        conn = psycopg2.connect(
            host=os.environ["POSTGRES_HOST"],
            port=os.environ["POSTGRES_PORT"], 
            database=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"]
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, product_name, description, indexed, indexed_at
                FROM products
                WHERE indexed = true
                ORDER BY indexed_at DESC
            """)
            results = cursor.fetchall()
        
        conn.close()
        
        documents = []
        for row in results:
            documents.append({
                "id": row[0],
                "title": row[1] or f"제품 {row[0]}",
                "product_name": row[1],
                "category": "product",
                "chunk_type": "product_info",
                "vector_count": 1,
                "created_at": row[4] or datetime.now()
            })
        
        return documents
        
    except Exception as e:
        logger.error(f"문서 목록 조회 실패: {str(e)}")
        return []

@app.post("/admin/documents")
async def create_document(request: DocumentCreateRequest):
    """새 문서 추가 (MVP에서는 미구현)"""
    # MVP에서는 제품 데이터만 사용하므로 수동 문서 추가는 미구현
    raise HTTPException(status_code=501, detail="MVP에서는 제품 데이터만 지원됩니다")

@app.delete("/admin/documents/{doc_id}")
async def delete_document(doc_id: int):
    """문서 삭제 (MVP에서는 미구현)"""
    # MVP에서는 제품 데이터 삭제는 위험하므로 미구현
    raise HTTPException(status_code=501, detail="MVP에서는 제품 데이터 삭제가 제한됩니다")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ["RAG_API_INTERNAL_PORT"])
    uvicorn.run(app, host="0.0.0.0", port=port)