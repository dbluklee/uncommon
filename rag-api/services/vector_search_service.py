"""
벡터 검색 서비스 모듈
비즈니스 로직과 검색 기능을 분리하여 재사용성과 유지보수성 향상
"""

import os
import logging
import time
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

# 프로젝트 모듈
from vector_store.milvus_store import ImprovedMilvusVectorStore
from retriever.retriever import get_retriever, AdvancedRetriever

logger = logging.getLogger(__name__)

class VectorSearchService:
    """벡터 검색 서비스 클래스"""
    
    def __init__(self, embedding_generator):
        """
        Args:
            embedding_generator: 임베딩 생성기
        """
        self.embedding_generator = embedding_generator
        self.collection_name = os.environ["COLLECTION_NAME"]
        
        # 벡터 스토어 초기화
        self._init_vector_store()
        
        # 고급 검색기 초기화
        self.advanced_retriever = AdvancedRetriever(self.vector_store)
    
    def _init_vector_store(self):
        """벡터 스토어 초기화"""
        try:
            logger.info("🔗 벡터 스토어 초기화 중...")
            self.vector_store = ImprovedMilvusVectorStore(
                collection_name=self.collection_name,
                embedding_model=self.embedding_generator
            )
            logger.info("✅ 벡터 스토어 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 벡터 스토어 초기화 실패: {str(e)}")
            raise
    
    async def search_similar_documents(self, 
                                     query: str, 
                                     top_k: int = 5,
                                     search_type: str = 'similarity') -> List[Dict[str, Any]]:
        """
        유사 문서 검색 (기본 검색 메서드)
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            search_type: 검색 타입
            
        Returns:
            검색 결과 리스트
        """
        try:
            search_start = time.time()
            logger.info(f"🔍 벡터 검색 시작: '{query[:50]}...' (top_k={top_k})")
            
            # 검색 수행
            if search_type == 'similarity':
                docs = self.vector_store.similarity_search_with_score(query, k=top_k)
            else:
                # 다른 검색 타입들을 위한 확장 가능
                retriever = get_retriever(self.vector_store, search_type, k=top_k)
                raw_docs = retriever.get_relevant_documents(query)
                docs = [(doc, doc.metadata.get('score', 0.0)) for doc in raw_docs]
            
            search_end = time.time()
            logger.info(f"⏱️ 검색 완료 시간: {search_end - search_start:.3f}초")
            
            # 결과 포맷팅
            results = []
            for doc, score in docs:
                result = {
                    "id": doc.metadata.get("id"),
                    "score": float(score),
                    "content": doc.page_content,
                    "metadata": {
                        "product_id": doc.metadata.get("product_id"),
                        "product_name": doc.metadata.get("product_name"),
                        "chunk_type": doc.metadata.get("chunk_type"),
                        "source": doc.metadata.get("source")
                    }
                }
                results.append(result)
            
            logger.info(f"✅ {len(results)}개 검색 결과 반환")
            return results
            
        except Exception as e:
            logger.error(f"❌ 벡터 검색 실패: {str(e)}")
            raise
    
    async def search_with_context_ranking(self, 
                                        query: str, 
                                        top_k: int = 5,
                                        use_mmr: bool = False) -> Dict[str, Any]:
        """
        컨텍스트 랭킹을 포함한 검색
        검색 결과를 품질별로 분류하여 반환
        """
        try:
            # 기본 검색 또는 MMR 검색
            if use_mmr:
                raw_results = self.advanced_retriever.hybrid_search(
                    query, use_mmr=True, k=top_k
                )
            else:
                docs = self.vector_store.similarity_search_with_score(query, k=top_k)
                raw_results = [{
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                } for doc, score in docs]
            
            # 결과 품질별 분류
            high_quality = []  # 스코어 > 0.8
            medium_quality = []  # 스코어 0.5 - 0.8
            low_quality = []   # 스코어 < 0.5
            
            for result in raw_results:
                score = result["score"]
                if score > 0.8:
                    high_quality.append(result)
                elif score > 0.5:
                    medium_quality.append(result)
                else:
                    low_quality.append(result)
            
            return {
                "query": query,
                "total_results": len(raw_results),
                "high_quality": high_quality,
                "medium_quality": medium_quality,
                "low_quality": low_quality,
                "all_results": raw_results
            }
            
        except Exception as e:
            logger.error(f"컨텍스트 랭킹 검색 실패: {str(e)}")
            raise
    
    async def search_by_product(self, 
                               query: str, 
                               product_filter: Dict[str, Any] = None,
                               top_k: int = 5) -> List[Dict[str, Any]]:
        """
        제품별 필터링 검색
        
        Args:
            query: 검색 쿼리
            product_filter: 제품 필터 조건
            top_k: 반환할 결과 수
        """
        try:
            if product_filter:
                results = self.advanced_retriever.search_with_metadata_filter(
                    query, product_filter, k=top_k
                )
            else:
                results = self.advanced_retriever.search_by_product_type(
                    query, k=top_k
                )
            
            logger.info(f"🔍 제품 필터링 검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"제품 필터링 검색 실패: {str(e)}")
            raise
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """서비스 통계 정보 반환"""
        try:
            vector_stats = self.vector_store.get_collection_stats()
            search_stats = self.advanced_retriever.get_search_stats()
            
            return {
                "service_status": "healthy",
                "collection_name": self.collection_name,
                "vector_store": vector_stats,
                "search_capabilities": {
                    "similarity_search": True,
                    "mmr_search": True,
                    "metadata_filtering": True,
                    "hybrid_search": True
                },
                "search_stats": search_stats
            }
            
        except Exception as e:
            logger.error(f"서비스 통계 조회 실패: {str(e)}")
            return {
                "service_status": "error",
                "error": str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """서비스 헬스체크"""
        try:
            # 벡터 스토어 상태 확인
            stats = self.vector_store.get_collection_stats()
            
            return {
                "status": "healthy",
                "vector_store_connected": True,
                "collection_loaded": stats.get("loaded", False),
                "document_count": stats.get("row_count", 0)
            }
            
        except Exception as e:
            logger.error(f"헬스체크 실패: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "vector_store_connected": False
            }