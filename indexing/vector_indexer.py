"""
벡터 인덱싱 모듈 - MVP 버전
Milvus에 벡터 저장
"""

import os
import logging
from typing import List, Dict, Any
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility

logger = logging.getLogger(__name__)

class VectorIndexer:
    """Milvus 벡터 인덱서"""
    
    def __init__(self):
        self.host = os.getenv('MILVUS_HOST', 'localhost')
        self.port = '19530'  # Milvus 내부 포트 (컨테이너 간 통신)
        self.collection_name = 'product_embeddings'
        self.dimension = 1024
        
        self.connect()
        self.setup_collection()
    
    def connect(self):
        """Milvus 연결"""
        connections.connect(
            alias="default",
            host=self.host,
            port=self.port
        )
        logger.info(f"Connected to Milvus at {self.host}:{self.port}")
    
    def setup_collection(self):
        """컬렉션 생성 또는 로드"""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            logger.info(f"Loaded collection: {self.collection_name}")
        else:
            self.create_collection()
            logger.info(f"Created collection: {self.collection_name}")
        
        self.collection.load()
    
    def create_collection(self):
        """새 컬렉션 생성"""
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="product_id", dtype=DataType.INT64),
            FieldSchema(name="chunk_id", dtype=DataType.INT64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension)
        ]
        
        schema = CollectionSchema(fields=fields, description="Product embeddings")
        self.collection = Collection(name=self.collection_name, schema=schema)
        
        # 인덱스 생성
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        self.collection.create_index(field_name="embedding", index_params=index_params)
    
    def index_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> int:
        """임베딩 저장"""
        if not embeddings_data:
            return 0
        
        # 데이터 준비
        product_ids = [item['product_id'] for item in embeddings_data]
        chunk_ids = [item['chunk_id'] for item in embeddings_data]
        texts = [item['text'] for item in embeddings_data]
        embeddings = [item['embedding'] for item in embeddings_data]
        
        # 삽입
        entities = [product_ids, chunk_ids, texts, embeddings]
        self.collection.insert(entities)
        self.collection.flush()
        
        logger.info(f"Indexed {len(embeddings_data)} vectors")
        return len(embeddings_data)
    
    def delete_product(self, product_id: int):
        """제품 벡터 삭제"""
        expr = f"product_id == {product_id}"
        self.collection.delete(expr)
        self.collection.flush()
        logger.info(f"Deleted vectors for product {product_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        return {
            "collection": self.collection_name,
            "num_entities": self.collection.num_entities
        }