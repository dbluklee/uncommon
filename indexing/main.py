"""
UNCOMMON 제품 인덱싱 서비스 - 개선된 버전
BGE-M3 + Milvus를 사용한 제품 데이터 벡터화
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from langchain_core.documents import Document
from dotenv import load_dotenv

# 프로젝트 모듈 임포트
from database import get_db, init_db, Product, ProductImage
from text_chunker import ProductTextChunker, ProductChunk
from embedding_generator import get_bge_m3_model
from milvus_client import ProductMilvusVectorStore

# 환경변수 로드
load_dotenv('../.env.global')
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱
app = FastAPI(
    title="UNCOMMON Indexing Service",
    description="제품 데이터 벡터화 및 Milvus 인덱싱 서비스",
    version="1.0.0"
)

# 전역 인스턴스
embedding_model = None
vector_store = None
chunker = None

# 요청/응답 모델
class IndexRequest(BaseModel):
    force_reindex: bool = False
    product_ids: List[int] = []  # 특정 제품만 인덱싱

class IndexResponse(BaseModel):
    message: str
    total_products: int
    indexed_count: int
    errors: List[str] = []

class StatsResponse(BaseModel):
    total_products: int
    indexed_products: int
    pending_products: int
    milvus_documents: int

# 인증
def verify_admin_key(x_api_key: str = Header(None)):
    admin_key = os.getenv('ADMIN_API_KEY')
    if not x_api_key or x_api_key != admin_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

def prepare_product_data(product: Product, images: List[ProductImage]) -> Dict[str, Any]:
    """DB 제품 데이터를 청킹에 적합한 형태로 준비"""
    
    # 제품 기본 정보
    product_data = {
        'id': product.id,
        'name': product.product_name,
        'url': product.source_global_url or product.source_kr_url,
        'price': str(product.price) if product.price else '',
        'brand': 'UNCOMMON',
        'category': 'eyewear'
    }
    
    # 모든 제품 정보를 문자열로 합치기
    description_parts = []
    
    # color 정보
    if product.color:
        description_parts.append(f"색상: {product.color}")
    
    # description 정보 (JSON 처리)
    if product.description:
        desc_str = str(product.description)
        if desc_str and desc_str != '{}':
            description_parts.append(f"설명: {desc_str}")
    
    # material 정보 (JSON 처리)  
    if product.material:
        material_str = str(product.material)
        if material_str and material_str != '{}':
            description_parts.append(f"재질: {material_str}")
    
    # size 정보 (JSON 처리)
    if product.size:
        size_str = str(product.size)
        if size_str and size_str != '{}':
            description_parts.append(f"사이즈: {size_str}")
    
    # reward_points 정보
    if product.reward_points:
        points_str = str(product.reward_points)
        if points_str and points_str != '{}':
            description_parts.append(f"리워드 포인트: {points_str}")
    
    # 설명 통합
    product_data['description'] = " | ".join(description_parts) if description_parts else ""
    
    # 이미지 정보
    if images:
        product_data['images'] = []
        for idx, img in enumerate(images):
            image_info = {
                'image_id': img.id,
                'image_order': img.image_order or idx,
                'size_bytes': len(img.image_data) if img.image_data else 0,
                'alt_text': f"제품 이미지 {idx + 1}",
                'context': f"제품 {product.product_name}의 {idx + 1}번째 이미지"
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

@app.post("/index/products", response_model=IndexResponse)
async def index_products(
    request: IndexRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_admin_key)
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
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_admin_key)
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
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_admin_key)
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
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_admin_key)
):
    """제품을 인덱스에서 제거 (미구현 - MVP에서는 제외)"""
    return {"message": "기능 미구현 - MVP 단계에서는 제외"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('INDEXING_PORT', 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)