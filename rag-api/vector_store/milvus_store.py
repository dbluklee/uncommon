"""
개선된 Milvus 벡터 스토어 모듈
레퍼런스 코드 기반으로 IP 메트릭과 HNSW 인덱스 최적화
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pymilvus import Collection, connections, utility
from langchain_core.documents import Document
from langchain.vectorstores.base import VectorStore

logger = logging.getLogger(__name__)

class ImprovedMilvusVectorStore(VectorStore):
    """개선된 Milvus 벡터 스토어 - 레퍼런스 코드 기반"""
    
    def __init__(self, 
                 collection_name: str,
                 embedding_model,
                 metric_type: str = None,
                 index_type: str = None,
                 milvus_host: str = None,
                 milvus_port: str = None):
        """
        Args:
            collection_name: Milvus 컬렉션 이름
            embedding_model: 임베딩 생성 모델
            metric_type: 메트릭 타입 (환경변수에서 자동 로드)
            index_type: 인덱스 타입 (환경변수에서 자동 로드)
            milvus_host: Milvus 호스트 (환경변수에서 자동 로드)
            milvus_port: Milvus 포트 (환경변수에서 자동 로드)
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # 환경변수에서 설정 로드
        self.metric_type = metric_type or os.environ.get("METRIC_TYPE", "IP")
        self.index_type = index_type or os.environ.get("INDEX_TYPE", "HNSW")
        self.milvus_host = milvus_host or os.environ["MILVUS_HOST"]
        self.milvus_port = milvus_port or os.environ["MILVUS_INTERNAL_PORT"]
        
        # Milvus 연결
        self._connect_milvus()
        
        # 컬렉션 로드
        self._load_collection()
    
    def _connect_milvus(self):
        """Milvus 서버 연결"""
        try:
            logger.info(f"🔗 Milvus 연결 시도: {self.milvus_host}:{self.milvus_port}")
            
            connections.connect(
                alias="default",
                host=self.milvus_host,
                port=self.milvus_port,
                timeout=30
            )
            
            # 서버 버전 정보로 연결 확인
            server_version = utility.get_server_version()
            logger.info(f"✅ Milvus 연결 성공! (서버 버전: {server_version})")
            
        except Exception as e:
            logger.error(f"❌ Milvus 연결 실패: {str(e)}")
            raise
    
    def _load_collection(self):
        """컬렉션 로드"""
        try:
            if not utility.has_collection(self.collection_name):
                logger.error(f"컬렉션 '{self.collection_name}'이 존재하지 않습니다")
                raise ValueError(f"Collection '{self.collection_name}' not found")
            
            self.collection = Collection(name=self.collection_name)
            self.collection.load()
            
            # 컬렉션 정보 확인
            total_docs = self.collection.num_entities
            logger.info(f"📊 컬렉션 총 문서 수: {total_docs}")
            logger.info(f"✅ 컬렉션 '{self.collection_name}' 로드 완료")
            
        except Exception as e:
            logger.error(f"컬렉션 로드 실패: {str(e)}")
            raise
    
    def _get_search_params(self) -> Dict[str, Any]:
        """인덱스 타입에 따른 검색 파라미터 반환"""
        if self.index_type == 'HNSW':
            params = {"ef": 64}
        elif self.index_type in ["IVF_FLAT", "IVF_SQ8", "IVF_PQ"]:
            params = {"nprobe": 10}
        else:
            params = {}
        
        return {
            "metric_type": self.metric_type,
            "params": params
        }
    
    def similarity_search(self, query: str, k: int = 4, **kwargs) -> List[Document]:
        """
        유사한 문서 검색 (LangChain 인터페이스)
        레퍼런스 코드 기반으로 개선
        """
        # 컬렉션 총 문서 수 확인
        self.collection.load()
        total_docs = self.collection.num_entities
        logger.info(f"📊 컬렉션 총 문서 수: {total_docs}")
        logger.info(f"📊 요청된 k 값: {k}")
        
        # 실제 k 값 조정
        actual_k = min(k, total_docs)
        logger.info(f"📊 실제 검색할 k 값: {actual_k}")
        
        if total_docs == 0:
            logger.warning("⚠️ 컬렉션에 문서가 없습니다!")
            return []
        
        # 쿼리 임베딩 생성
        logger.info(f"🔍 쿼리 임베딩 생성: '{query[:50]}...'")
        query_vector = self.embedding_model.generate_query_embedding(query)
        logger.info(f"📏 쿼리 벡터 차원: {len(query_vector)}")
        
        # 검색 파라미터 설정
        search_params = self._get_search_params()
        logger.info(f"🔧 검색 파라미터:")
        logger.info(f"   - metric_type: {search_params['metric_type']}")
        logger.info(f"   - index_type: {self.index_type}")
        logger.info(f"   - params: {search_params['params']}")
        logger.info(f"   - limit: {actual_k}")
        
        # 검색 실행
        logger.info("🔍 벡터 검색 실행 중...")
        try:
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=actual_k,
                output_fields=["product_id", "product_name", "chunk_type", "source", "content"]
            )
            
            logger.info("✅ 검색 완료!")
            logger.info(f"📊 검색 결과 개수: {len(results[0]) if results else 0}")
            
            # 각 결과의 상세 정보 출력
            if results and len(results[0]) > 0:
                for i, hit in enumerate(results[0]):
                    logger.info(f"   결과 {i+1}: score={hit.score:.4f}, id={hit.id}")
                    logger.info(f"          product_name: {hit.entity.get('product_name', 'N/A')}")
                    logger.info(f"          content 길이: {len(hit.entity.get('content', ''))}")
            
        except Exception as e:
            logger.error(f"❌ 검색 중 오류: {e}")
            return []
        
        # LangChain Document 형식으로 변환
        logger.info("🔄 LangChain Document 형식으로 변환 중...")
        docs = []
        for hits in results:
            for hit in hits:
                doc = Document(
                    page_content=hit.entity.get("content", ""),
                    metadata={
                        "product_id": hit.entity.get("product_id"),
                        "product_name": hit.entity.get("product_name"),
                        "chunk_type": hit.entity.get("chunk_type"),
                        "source": hit.entity.get("source"),
                        "score": hit.score,
                        "id": hit.id
                    }
                )
                docs.append(doc)
        
        logger.info(f"✅ {len(docs)}개 문서를 LangChain Document로 변환 완료")
        return docs
    
    def similarity_search_with_score(self, query: str, k: int = 4, **kwargs) -> List[tuple]:
        """유사도 점수와 함께 검색"""
        docs = self.similarity_search(query, k, **kwargs)
        return [(doc, doc.metadata.get('score', 0.0)) for doc in docs]
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[dict]] = None, **kwargs) -> List[str]:
        """텍스트 리스트를 벡터 스토어에 추가 (미구현 - 인덱싱 서비스에서 처리)"""
        logger.warning("텍스트 추가는 인덱싱 서비스에서 처리됩니다")
        return []
    
    def add_documents(self, documents: List[Document], **kwargs) -> List[str]:
        """Document 객체 리스트를 벡터 스토어에 추가 (미구현 - 인덱싱 서비스에서 처리)"""
        logger.warning("문서 추가는 인덱싱 서비스에서 처리됩니다")
        return []

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding_model,
        metadatas: Optional[List[dict]] = None,
        **kwargs
    ) -> "ImprovedMilvusVectorStore":
        """텍스트 리스트로부터 벡터 스토어 생성 (미구현 - 인덱싱 서비스에서 처리)"""
        logger.warning("from_texts는 인덱싱 서비스에서 처리됩니다. 빈 벡터 스토어를 반환합니다.")
        return cls(
            collection_name=kwargs.get("collection_name", "default"),
            embedding_model=embedding_model,
            **kwargs
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 정보 반환"""
        try:
            return {
                "collection_name": self.collection_name,
                "row_count": self.collection.num_entities,
                "loaded": True,
                "metric_type": self.metric_type,
                "index_type": self.index_type
            }
        except Exception as e:
            logger.error(f"통계 조회 실패: {str(e)}")
            return {"error": str(e)}