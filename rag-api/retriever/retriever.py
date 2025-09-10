"""
검색 타입별 Retriever 모듈
레퍼런스 코드 기반으로 다양한 검색 전략 제공
"""

import os
import logging
from typing import List, Dict, Any
from langchain_core.vectorstores import VectorStoreRetriever
from langchain.vectorstores.base import VectorStore

logger = logging.getLogger(__name__)

def get_retriever(
    vector_db: VectorStore,
    retriever_type: str = 'top_k',
    **kwargs
) -> VectorStoreRetriever:
    """
    검색 타입에 따른 Retriever 반환
    
    Args:
        vector_db: 벡터 데이터베이스
        retriever_type: 검색 타입 ('top_k', 'threshold', 'mmr')
        **kwargs: 추가 검색 파라미터
        
    Returns:
        VectorStoreRetriever: 설정된 리트리버
    """
    
    # 환경변수에서 기본값 로드
    default_k = int(os.environ.get("RETRIEVAL_TOP_K", 4))
    
    if retriever_type == 'top_k':
        k = kwargs.get('k', default_k)
        retriever = vector_db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        logger.info(f"✅ 'top_k' 타입 retriever 생성 (k={k})")
    
    elif retriever_type == 'threshold':
        score_threshold = kwargs.get('score_threshold', 0.2)
        retriever = vector_db.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": score_threshold}
        )
        logger.info(f"✅ 'threshold' 타입 retriever 생성 (threshold={score_threshold})")
    
    elif retriever_type == 'mmr':
        k = kwargs.get('k', default_k)
        fetch_k = kwargs.get('fetch_k', 20)
        retriever = vector_db.as_retriever(
            search_type="mmr",
            search_kwargs={'k': k, 'fetch_k': fetch_k}
        )
        logger.info(f"✅ 'mmr' 타입 retriever 생성 (k={k}, fetch_k={fetch_k})")
    
    else:
        # 기본값: similarity 검색
        k = kwargs.get('k', default_k)
        retriever = vector_db.as_retriever(
            search_kwargs={'k': k}
        )
        logger.info(f"✅ '기본' 타입 retriever 생성 (k={k})")
    
    return retriever


class AdvancedRetriever:
    """고급 검색 기능을 제공하는 Retriever 클래스"""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.default_k = int(os.environ.get("RETRIEVAL_TOP_K", 4))
    
    def search_with_metadata_filter(self, 
                                   query: str, 
                                   metadata_filter: Dict[str, Any],
                                   k: int = None) -> List[Dict[str, Any]]:
        """메타데이터 필터를 적용한 검색"""
        k = k or self.default_k
        
        try:
            # 기본 검색 수행
            docs = self.vector_store.similarity_search_with_score(query, k=k*2)  # 여유분 확보
            
            # 메타데이터 필터 적용
            filtered_docs = []
            for doc, score in docs:
                match = True
                for key, value in metadata_filter.items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break
                
                if match:
                    filtered_docs.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": score
                    })
                
                if len(filtered_docs) >= k:
                    break
            
            logger.info(f"🔍 메타데이터 필터 검색 완료: {len(filtered_docs)}개 결과")
            return filtered_docs
            
        except Exception as e:
            logger.error(f"메타데이터 필터 검색 실패: {str(e)}")
            return []
    
    def search_by_product_type(self, 
                              query: str, 
                              product_type: str = None,
                              k: int = None) -> List[Dict[str, Any]]:
        """제품 타입별 검색"""
        k = k or self.default_k
        
        if product_type:
            return self.search_with_metadata_filter(
                query, 
                {"chunk_type": product_type}, 
                k=k
            )
        else:
            # 일반 검색
            docs = self.vector_store.similarity_search_with_score(query, k=k)
            return [{
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            } for doc, score in docs]
    
    def hybrid_search(self, 
                     query: str, 
                     use_mmr: bool = False,
                     k: int = None) -> List[Dict[str, Any]]:
        """하이브리드 검색 (유사도 + MMR)"""
        k = k or self.default_k
        
        try:
            if use_mmr:
                # MMR 검색 사용
                retriever = get_retriever(self.vector_store, 'mmr', k=k, fetch_k=k*5)
                docs = retriever.get_relevant_documents(query)
                
                results = []
                for doc in docs:
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": doc.metadata.get('score', 0.0)
                    })
                
                logger.info(f"🔍 MMR 하이브리드 검색 완료: {len(results)}개 결과")
                return results
            else:
                # 일반 유사도 검색
                return self.search_by_product_type(query, k=k)
                
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {str(e)}")
            return []
    
    def get_search_stats(self) -> Dict[str, Any]:
        """검색 통계 반환"""
        try:
            return self.vector_store.get_collection_stats()
        except Exception as e:
            logger.error(f"검색 통계 조회 실패: {str(e)}")
            return {"error": str(e)}