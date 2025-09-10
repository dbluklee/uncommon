# RAG LLM 시스템의 벡터 인덱싱 서비스 메인 파일
# 목적: 스크래핑된 제품 데이터를 BGE-M3 모델로 벡터화하여 Milvus DB에 저장
# 관련 함수: process_products_indexing (벡터화), ProductTextChunker.chunk_product_data (청킹)
# 주요 기능: 텍스트 청킹, BGE-M3 임베딩, Milvus 벡터 저장, 자동 인덱싱
"""
UNCOMMON 제품 인덱싱 서비스 - BGE-M3 임베딩 모델과 Milvus 벡터 데이터베이스를 활용한 제품 데이터 벡터화
목적: PostgreSQL의 제품 데이터를 검색 가능한 벡터로 변환하여 RAG 시스템의 검색 성능 최적화
"""

import os
import json
import logging  # 인덱싱 작업 상세 로깅
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel  # API 요청/응답 모델 정의
from sqlalchemy.orm import Session  # PostgreSQL ORM 세션
from langchain_core.documents import Document  # LangChain 문서 형태로 변환
from dotenv import load_dotenv  # 환경변수 로드

# 프로젝트 핵심 모듈 임포트 - 각각 특화된 벡터화 기능 담당
from database import get_db, init_db, Product, ProductImage  # DB 연결 및 제품 모델
from text_chunker import ProductTextChunker, ProductChunk  # 제품 특화 텍스트 청킹
from embedding_generator import get_bge_m3_model  # BGE-M3 임베딩 모델 로더
from milvus_client import ProductMilvusVectorStore  # Milvus 벡터 저장소

# 환경변수 및 서비스 초기화 설정
# .env.global에서 Milvus, BGE-M3 모델 관련 설정 로드
load_dotenv('../.env.global')  # 프로젝트 전역 환경변수
load_dotenv()  # 로컬 환경변수 (우선순위 높음)

# 인덱싱 작업 상세 로깅 설정 - 벡터화 과정 추적용
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 초기화 - 벡터 인덱싱 전용 API 서비스
app = FastAPI(
    title="UNCOMMON Indexing Service",
    description="제품 데이터 벡터화 및 Milvus 인덱싱 서비스",
    version="1.0.0"
)

# 전역 AI/ML 모델 인스턴스 - 서비스 시작 시 한 번만 로드하여 메모리 효율성 확보
embedding_model = None  # BGE-M3 임베딩 모델 (BAAI/bge-m3)
vector_store = None  # Milvus 벡터 스토어 클라이언트
chunker = None  # 제품 텍스트 청킹 모듈

# API 요청/응답 데이터 모델 - 클라이언트와 서버 간 인덱싱 작업 파라미터 정의
# IndexRequest: 인덱싱 옵션 설정 (전체/부분, 강제 재인덱싱)
# IndexResponse: 인덱싱 결과 정보 (성공/실패 건수, 오류 메시지)
# StatsResponse: 시스템 전체 인덱싱 현황 통계
class IndexRequest(BaseModel):
    force_reindex: bool = False  # 기존 인덱싱된 제품도 재처리 여부
    product_ids: List[int] = []  # 특정 제품 ID만 인덱싱 (빈 리스트면 전체)

class IndexResponse(BaseModel):
    message: str  # 인덱싱 작업 상태 메시지
    total_products: int  # 처리 대상 제품 총 개수
    indexed_count: int  # 성공적으로 인덱싱된 제품 수
    errors: List[str] = []  # 인덱싱 실패 시 오류 메시지 목록

class StatsResponse(BaseModel):
    total_products: int  # PostgreSQL 전체 제품 수
    indexed_products: int  # 인덱싱 완료된 제품 수
    pending_products: int  # 인덱싱 대기 중인 제품 수
    milvus_documents: int  # Milvus에 저장된 실제 벡터 문서 수

# Admin authentication removed for MVP

# 제품 데이터 전처리 함수 - PostgreSQL 제품 데이터를 벡터화에 최적화된 형태로 변환
# 목적: DB의 정규화된 데이터를 검색용 텍스트로 통합, 다국어 정보 병합
# 관련 함수: ProductTextChunker.chunk_product_data (청킹 처리)
# 입력: Product 모델, ProductImage 리스트
# 출력: 청킹에 적합한 Dict 형태 제품 정보
def prepare_product_data(product: Product, images: List[ProductImage]) -> Dict[str, Any]:
    """DB 제품 데이터를 청킹에 적합한 형태로 준비 - JSONB 필드 파싱 및 텍스트 통합"""
    
    # 제품 메타데이터 구성 - 검색 시 필터링 및 결과 표시용
    product_data = {
        'id': product.id,  # 제품 고유 식별자
        'name': product.product_name,  # 제품명 (주 검색 대상)
        'url': product.source_global_url or product.source_kr_url,  # 제품 페이지 링크
        'price': str(product.price) if product.price else '',  # 가격 정보
        'brand': 'UNCOMMON',  # 브랜드명 (고정값)
        'category': 'eyewear'  # 제품 카테고리 (안경)
    }
    
    # 제품의 모든 속성 정보를 검색 가능한 텍스트로 통합
    # PostgreSQL JSONB 필드들을 파싱하여 자연어 형태로 변환
    description_parts = []
    
    # 색상 정보 추가 - 사용자가 "빨간 안경" 등으로 검색 시 매칭
    if product.color:
        description_parts.append(f"색상: {product.color}")
    
    # 제품 상세 설명 (JSONB) - 영문/한글 버전 모두 포함
    if product.description:
        desc_str = str(product.description)
        if desc_str and desc_str != '{}':
            description_parts.append(f"설명: {desc_str}")
    
    # 재질/소재 정보 (JSONB) - "아세테이트 안경" 등 재질 기반 검색 지원
    if product.material:
        material_str = str(product.material)
        if material_str and material_str != '{}':
            description_parts.append(f"재질: {material_str}")
    
    # 사이즈 정보 (JSONB) - "큰 안경", "작은 프레임" 등 크기 관련 검색
    if product.size:
        size_str = str(product.size)
        if size_str and size_str != '{}':
            description_parts.append(f"사이즈: {size_str}")
    
    # 리워드 포인트 정보 - 혜택 관련 검색 시 활용
    if product.reward_points:
        points_str = str(product.reward_points)
        if points_str and points_str != '{}':
            description_parts.append(f"리워드 포인트: {points_str}")
    
    # 모든 제품 속성을 하나의 검색 가능한 텍스트로 통합
    product_data['description'] = " | ".join(description_parts) if description_parts else ""
    
    # 제품 이미지 메타데이터 구성 - 멀티모달 검색 지원용
    # 이미지 바이너리는 PostgreSQL에 저장, 메타데이터만 벡터화
    if images:
        product_data['images'] = []
        for idx, img in enumerate(images):
            # 각 이미지의 검색 가능한 메타데이터 생성
            image_info = {
                'image_id': img.id,  # 이미지 DB 고유 ID
                'image_order': img.image_order or idx,  # 이미지 표시 순서
                'size_bytes': len(img.image_data) if img.image_data else 0,  # 이미지 크기
                'alt_text': f"제품 이미지 {idx + 1}",  # 대체 텍스트
                'context': f"제품 {product.product_name}의 {idx + 1}번째 이미지"  # 검색 컨텍스트
            }
            product_data['images'].append(image_info)
    
    return product_data

async def process_products_indexing(product_ids: List[int] = None, force_reindex: bool = False):
    """제품 인덱싱 백그라운드 작업"""
    db = next(get_db())
    errors = []
    indexed_count = 0
    
    try:
        # 처리할 제품 선택
        query = db.query(Product)
        
        if product_ids:
            query = query.filter(Product.id.in_(product_ids))
        elif not force_reindex:
            query = query.filter(Product.indexed == False)
            
        products = query.all()
        
        logger.info(f"🚀 {len(products)}개 제품 인덱싱 시작")
        
        # 제품별 처리
        for product in products:
            try:
                logger.info(f"📦 제품 {product.id} ({product.product_name}) 처리 중...")
                
                # 이미지 정보 조회
                images = db.query(ProductImage).filter(ProductImage.product_id == product.id).all()
                
                # 제품 데이터 준비
                product_data = prepare_product_data(product, images)
                
                # 청킹
                chunks = chunker.chunk_product_data(product_data)
                logger.info(f"  📄 {len(chunks)}개 청크 생성")
                
                # 청킹 결과 상세 출력
                for i, chunk in enumerate(chunks, 1):
                    logger.info(f"  🔵 청크 {i}/{len(chunks)}:")
                    logger.info(f"     📝 내용: {chunk.page_content[:200]}...")
                    logger.info(f"     🏷️  메타데이터: {chunk.metadata}")
                
                if not chunks:
                    logger.warning(f"  ⚠️ 제품 {product.id}: 청크가 생성되지 않음")
                    continue
                
                # LangChain Document 변환
                documents = []
                for chunk in chunks:
                    doc = Document(
                        page_content=chunk.page_content,
                        metadata=chunk.metadata
                    )
                    documents.append(doc)
                
                # Milvus에 저장
                if documents:
                    vector_store.add_documents(documents)
                    logger.info(f"  ✅ 제품 {product.id}: {len(documents)}개 문서 Milvus 저장 완료")
                    
                    # 상태 업데이트
                    product.indexed = True
                    product.indexed_at = datetime.utcnow()
                    db.commit()
                    
                    indexed_count += 1
                else:
                    logger.warning(f"  ⚠️ 제품 {product.id}: 문서가 생성되지 않음")
                
            except Exception as e:
                error_msg = f"제품 {product.id} 인덱싱 실패: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        logger.info(f"🎉 인덱싱 완료: {indexed_count}개 성공, {len(errors)}개 오류")
        return indexed_count, errors
        
    except Exception as e:
        error_msg = f"인덱싱 작업 전체 실패: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        return indexed_count, errors
    finally:
        db.close()

# API 엔드포인트
@app.on_event("startup")
async def startup():
    """서비스 시작 시 초기화"""
    global embedding_model, vector_store, chunker
    
    logger.info("🚀 UNCOMMON 인덱싱 서비스 시작")
    
    try:
        # DB 초기화
        init_db()
        logger.info("✅ 데이터베이스 초기화 완료")
        
        # BGE-M3 임베딩 모델 로드
        logger.info("📥 BGE-M3 임베딩 모델 로딩 중...")
        embedding_model = get_bge_m3_model()
        logger.info("✅ 임베딩 모델 로딩 완료")
        
        # Milvus 벡터 스토어 초기화
        logger.info("🔗 Milvus 벡터 스토어 초기화 중...")
        vector_store = ProductMilvusVectorStore(
            collection_name="uncommon_products",
            embedding_model=embedding_model,
            always_new=False  # 기존 데이터 유지
        )
        logger.info("✅ Milvus 벡터 스토어 초기화 완료")
        
        # 청킹 모듈 초기화
        chunker = ProductTextChunker(chunk_size=500)
        logger.info("✅ 제품 청킹 모듈 초기화 완료")
        
        logger.info("🎉 모든 모듈 초기화 완료!")
        
    except Exception as e:
        logger.error(f"❌ 서비스 초기화 실패: {e}")
        raise

@app.get("/")
async def root():
    """서비스 상태 확인"""
    return {
        "service": "UNCOMMON Indexing Service",
        "status": "running",
        "version": "1.0.0",
        "embedding_model": "BGE-M3",
        "vector_store": "Milvus"
    }

@app.get("/health")
async def health_check():
    """서비스 헬스체크"""
    return {
        "status": "healthy",
        "service": "indexing"
    }

@app.post("/index/products", response_model=IndexResponse)
async def index_products(
    request: IndexRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """제품 인덱싱 시작"""
    
    # 처리할 제품 수 확인
    query = db.query(Product)
    
    if request.product_ids:
        query = query.filter(Product.id.in_(request.product_ids))
        total_count = len(request.product_ids)
    elif request.force_reindex:
        total_count = query.count()
    else:
        total_count = query.filter(Product.indexed == False).count()
    
    if total_count == 0:
        return IndexResponse(
            message="인덱싱할 제품이 없습니다",
            total_products=0,
            indexed_count=0
        )
    
    # 백그라운드 작업 시작
    background_tasks.add_task(
        process_products_indexing,
        request.product_ids if request.product_ids else None,
        request.force_reindex
    )
    
    return IndexResponse(
        message=f"인덱싱 시작: {total_count}개 제품 처리 예정",
        total_products=total_count,
        indexed_count=0
    )

@app.get("/index/stats", response_model=StatsResponse)
async def get_indexing_stats(
    db: Session = Depends(get_db)
):
    """인덱싱 통계 조회"""
    
    total_products = db.query(Product).count()
    indexed_products = db.query(Product).filter(Product.indexed == True).count()
    pending_products = total_products - indexed_products
    
    # Milvus 문서 수 확인
    try:
        if vector_store and vector_store.collection:
            milvus_docs = vector_store.collection.num_entities
        else:
            milvus_docs = 0
    except:
        milvus_docs = 0
    
    return StatsResponse(
        total_products=total_products,
        indexed_products=indexed_products,
        pending_products=pending_products,
        milvus_documents=milvus_docs
    )

@app.post("/index/products/{product_id}")
async def index_single_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """단일 제품 즉시 인덱싱"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        # 이미지 정보 조회
        images = db.query(ProductImage).filter(ProductImage.product_id == product_id).all()
        
        # 제품 데이터 준비
        product_data = prepare_product_data(product, images)
        
        # 청킹
        chunks = chunker.chunk_product_data(product_data)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks generated for this product")
        
        # LangChain Document 변환
        documents = []
        for chunk in chunks:
            doc = Document(
                page_content=chunk.page_content,
                metadata=chunk.metadata
            )
            documents.append(doc)
        
        # Milvus에 저장
        vector_store.add_documents(documents)
        
        # 상태 업데이트
        product.indexed = True
        product.indexed_at = datetime.utcnow()
        db.commit()
        
        return {
            "message": f"제품 {product_id} 인덱싱 완료",
            "product_name": product.product_name,
            "chunks_created": len(chunks),
            "documents_indexed": len(documents)
        }
        
    except Exception as e:
        logger.error(f"제품 {product_id} 인덱싱 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/index/products/{product_id}")
async def remove_product_from_index(
    product_id: int,
    db: Session = Depends(get_db)
):
    """제품을 인덱스에서 제거 (미구현 - MVP에서는 제외)"""
    return {"message": "기능 미구현 - MVP 단계에서는 제외"}

@app.post("/process/new-products")
async def process_new_products(
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """스크래핑 완료 후 자동 인덱싱 시작 (스크래퍼에서 호출)"""
    
    products_count = request.get("products_count", 0)
    logger.info(f"📬 스크래퍼로부터 알림 받음: {products_count}개 제품 스크래핑 완료")
    
    # 인덱싱되지 않은 제품 수 확인
    pending_count = db.query(Product).filter(Product.indexed == False).count()
    
    if pending_count == 0:
        return {
            "message": f"스크래핑 알림 수신: {products_count}개 제품, 인덱싱할 제품 없음",
            "products_scraped": products_count,
            "products_to_index": 0
        }
    
    # 백그라운드 자동 인덱싱 시작
    background_tasks.add_task(
        process_products_indexing,
        None,  # product_ids = None (모든 미인덱싱 제품)
        False  # force_reindex = False
    )
    
    logger.info(f"🚀 자동 인덱싱 시작: {pending_count}개 제품 처리 예정")
    
    return {
        "message": f"스크래핑 완료 알림 수신, 자동 인덱싱 시작",
        "products_scraped": products_count,
        "products_to_index": pending_count,
        "status": "indexing_started"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ['INDEXING_INTERNAL_PORT'])
    uvicorn.run(app, host="0.0.0.0", port=port)