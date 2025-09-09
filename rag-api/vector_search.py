"""
벡터 검색 모듈
Milvus를 사용한 유사도 검색
"""

import os
import logging
from typing import List, Dict, Any
from pymilvus import Collection, connections, utility
import json
import time

logger = logging.getLogger(__name__)

class VectorSearcher:
    """Milvus 벡터 검색기"""
    
    def __init__(self, embedding_generator):
        """벡터 검색기 초기화"""
        self.embedding_generator = embedding_generator
        self.collection_name = os.getenv("COLLECTION_NAME", "uncommon_products")
        
        # Milvus 연결
        self._connect_milvus()
        
        # 컬렉션 로드
        self._load_collection()
    
    def _connect_milvus(self):
        """Milvus 서버 연결"""
        try:
            milvus_host = os.getenv("MILVUS_HOST", "localhost")
            milvus_port = os.getenv("MILVUS_INTERNAL_PORT", "19530")
            
            logger.info(f"🔗 Milvus 연결 시도: {milvus_host}:{milvus_port}")
            
            connections.connect(
                alias="default",
                host=milvus_host,
                port=milvus_port,
                timeout=30
            )
            
            # 연결 확인
            if utility.has_collection(self.collection_name):
                logger.info(f"✅ Milvus 연결 성공! 컬렉션: {self.collection_name}")
            else:
                logger.warning(f"⚠️ 컬렉션 '{self.collection_name}'이 존재하지 않습니다")
                
        except Exception as e:
            logger.error(f"❌ Milvus 연결 실패: {str(e)}")
            raise
    
    def _load_collection(self):
        """컬렉션 로드"""
        try:
            if not utility.has_collection(self.collection_name):
                logger.error(f"컬렉션 '{self.collection_name}'이 존재하지 않습니다")
                return
            
            self.collection = Collection(name=self.collection_name)
            self.collection.load()
            
            # 컬렉션 정보 확인
            num_entities = self.collection.num_entities
            logger.info(f"📊 컬렉션 로드 완료: {num_entities}개 벡터")
            
        except Exception as e:
            logger.error(f"컬렉션 로드 실패: {str(e)}")
            raise
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        벡터 유사도 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            
        Returns:
            검색 결과 리스트
        """
        try:
            # 쿼리 임베딩 생성
            embed_start = time.time()
            logger.info(f"🔍 쿼리 임베딩 생성: {query[:50]}...")
            query_embedding = self.embedding_generator.generate_query_embedding(query)
            embed_end = time.time()
            logger.info(f"⏱️ 임베딩 생성 시간: {embed_end - embed_start:.3f}초")
            
            # 검색 파라미터
            search_params = {
                "metric_type": "IP",  # Inner Product (코사인 유사도와 유사)
                "params": {"nprobe": 10}
            }
            
            # 출력 필드 설정
            output_fields = ["product_id", "product_name", "chunk_type", "source", "content"]
            
            # 벡터 검색 수행
            milvus_start = time.time()
            logger.info(f"🔎 Milvus 검색 중 (top_k={top_k})...")
            search_results = self.collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=output_fields
            )
            milvus_end = time.time()
            logger.info(f"⏱️ Milvus 검색 시간: {milvus_end - milvus_start:.3f}초")
            
            # 결과 포맷팅
            formatted_results = []
            for hits in search_results:
                for hit in hits:
                    # Milvus 검색 결과에서 필드 추출 (hit.fields 사용)
                    fields = hit.fields
                    result = {
                        "id": hit.id,
                        "score": float(hit.score),
                        "content": fields.get("content", ""),
                        "product_id": fields.get("product_id", 0),
                        "product_name": fields.get("product_name", ""),
                        "chunk_type": fields.get("chunk_type", ""),
                        "source": fields.get("source", "")
                    }
                    formatted_results.append(result)
            
            logger.info(f"✅ {len(formatted_results)}개 결과 검색 완료")
            
            # 점수 기준 정렬 (높은 점수 우선)
            formatted_results.sort(key=lambda x: x["score"], reverse=True)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"검색 실패: {str(e)}")
            raise
    
    async def search_with_filter(self, query: str, filter_expr: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        필터를 포함한 벡터 검색
        
        Args:
            query: 검색 쿼리
            filter_expr: Milvus 필터 표현식 (예: "product_id in [1, 2, 3]")
            top_k: 반환할 결과 수
            
        Returns:
            검색 결과 리스트
        """
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embedding_generator.generate_query_embedding(query)
            
            # 검색 파라미터
            search_params = {
                "metric_type": "IP",
                "params": {"nprobe": 10}
            }
            
            # 필터를 포함한 검색
            search_results = self.collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["product_id", "product_name", "chunk_type", "source", "content"]
            )
            
            # 결과 포맷팅 (위와 동일)
            formatted_results = []
            for hits in search_results:
                for hit in hits:
                    # Milvus 검색 결과에서 필드 추출 (hit.fields 사용)
                    fields = hit.fields
                    result = {
                        "id": hit.id,
                        "score": float(hit.score),
                        "content": fields.get("content", ""),
                        "product_id": fields.get("product_id", 0),
                        "product_name": fields.get("product_name", ""),
                        "chunk_type": fields.get("chunk_type", ""),
                        "source": fields.get("source", "")
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"필터 검색 실패: {str(e)}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 정보 반환"""
        try:
            if not hasattr(self, 'collection'):
                return {"error": "Collection not loaded"}
            
            return {
                "collection_name": self.collection_name,
                "row_count": self.collection.num_entities,
                "loaded": True
            }
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {str(e)}")
            return {"error": str(e)}
    
    def release_collection(self):
        """컬렉션 언로드 (메모리 해제)"""
        try:
            if hasattr(self, 'collection'):
                self.collection.release()
                logger.info(f"컬렉션 '{self.collection_name}' 언로드 완료")
        except Exception as e:
            logger.error(f"컬렉션 언로드 실패: {str(e)}")