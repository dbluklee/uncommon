"""
Milvus 벡터 데이터베이스 클라이언트 - UNCOMMON 프로젝트 전용
langchain-milvus를 사용한 고도화된 벡터 스토어
"""

from typing import List, Dict, Any, Optional
from langchain_milvus import Milvus
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.documents import Document
from langchain.vectorstores.base import VectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from pymilvus import connections, utility, FieldSchema, CollectionSchema, DataType, Collection
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env.global')
load_dotenv()

logger = logging.getLogger(__name__)

class ProductMilvusVectorStore(VectorStore):
    """제품 데이터 전용 Milvus 벡터 스토어"""
    
    def __init__(self, 
                 collection_name: str = "uncommon_products",
                 embedding_model: HuggingFaceEmbeddings = None,
                 metric_type: str = 'IP',
                 index_type: str = 'HNSW',
                 milvus_host: str = None,
                 milvus_port: str = None,
                 always_new: bool = False):
        """
        Milvus Vector Store for UNCOMMON Products
        
        Args:
            collection_name: Milvus 컬렉션 이름
            embedding_model: 임베딩 생성용 모델
            milvus_host: Milvus 서버 호스트
            milvus_port: Milvus 서버 포트
            always_new: 기존 컬렉션 삭제 후 새로 생성 여부
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.embedding_dim = 1024  # BAAI/bge-m3 모델의 임베딩 차원
        self.always_new = always_new
        self.metric_type = metric_type
        self.index_type = index_type
        
        # 환경변수에서 Milvus 접속 정보 가져오기 (컨테이너 간 통신용 내부 포트 사용)
        self.milvus_host = milvus_host or os.environ['MILVUS_HOST']
        self.milvus_port = milvus_port or os.environ['MILVUS_INTERNAL_PORT']
        
        # Milvus 연결
        print(f"\n🔗 Milvus 연결 시도: {self.milvus_host}:{self.milvus_port}")
        connections.connect("default", host=self.milvus_host, port=self.milvus_port)

        # 서버 버전 정보를 요청하여 실제 통신 확인
        server_version = utility.get_server_version()
        print(f"✅ Milvus 연결 성공! (서버 버전: {server_version})")
        
        # 컬렉션 생성 또는 로드
        self._setup_collection()

    def _setup_collection(self):
        """Milvus 컬렉션 설정"""
        print(f"\n📋 컬렉션 설정: {self.collection_name}")
        
        # 스키마 정의
        fields = [
            # id 필드 (자동 ID 생성)
            FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, auto_id=True, max_length=100),
            # 벡터를 저장할 필드
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
            # 제품 정보 필드들
            FieldSchema(name="product_id", dtype=DataType.INT64),
            FieldSchema(name="product_name", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="chunk_type", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=200),
            # 원본 텍스트를 저장할 필드
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535)
        ]
        
        schema = CollectionSchema(fields, f"'{self.collection_name}' UNCOMMON Product Documents")
        
        if self.always_new:
            # 기존 컬렉션이 있으면 삭제
            if utility.has_collection(self.collection_name):
                print(f"🗑️ 기존 컬렉션 '{self.collection_name}' 삭제")
                utility.drop_collection(self.collection_name)

        # 컬렉션 생성
        try:
            self.collection = Collection(self.collection_name, schema)
            print(f"✅ 새 컬렉션 '{self.collection_name}' 생성")
        except Exception:
            self.collection = Collection(self.collection_name)
            print(f"✅ 기존 컬렉션 '{self.collection_name}' 로드")
        
        # 인덱스 생성
        self._create_index()

    def _create_index(self):
        """벡터 필드에 인덱스 생성"""
        if self.index_type == 'HNSW':
            params = {"M": 8, "efConstruction": 64}
        elif self.index_type in ["IVF_FLAT", "IVF_SQ8", "IVF_PQ"]:
            params = {"nlist": 128}
        else:
            params = {}

        index_params = {
            "metric_type": self.metric_type,  
            "index_type": self.index_type,
            "params": params
        }
        
        try:
            print(f"🔧 벡터 인덱스 생성 중...")
            self.collection.create_index("vector", index_params)
            print(f"✅ 인덱스 생성 완료 (metric_type: {self.metric_type}, index_type: {self.index_type})")
        except Exception as e:
            print(f"⚠️ 인덱스 생성 오류 (이미 존재할 수 있음): {e}")

    def add_texts(self, texts: List[str], metadatas: Optional[List[dict]] = None, **kwargs) -> List[str]:
        """
        텍스트 리스트를 벡터 스토어에 추가 (배치 처리)
        """
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        print(f"\n📤 {len(texts)}개 문서를 배치로 처리합니다...")
        
        # 배치 크기 설정 (GPU 메모리에 따라 조정)
        BATCH_SIZE = 16  # 한 번에 16개씩 처리
        
        # 전체 데이터를 배치로 나누어 처리
        all_vectors = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[i:i+BATCH_SIZE]
            print(f"   배치 {i//BATCH_SIZE + 1}/{(len(texts)-1)//BATCH_SIZE + 1}: {len(batch_texts)}개 문서 임베딩 중...")
            
            try:
                # 배치별 임베딩 생성
                batch_vectors = self.embedding_model.embed_documents(batch_texts)
                all_vectors.extend(batch_vectors)
                print(f"   ✅ 배치 완료 ({len(batch_vectors)}개 벡터 생성)")
                
            except RuntimeError as e:
                if "CUDA" in str(e):
                    print(f"   ❌ CUDA 메모리 오류 발생, 더 작은 배치로 재시도...")
                    # 더 작은 배치로 재시도
                    for j in range(i, min(i+BATCH_SIZE, len(texts))):
                        single_vector = self.embedding_model.embed_documents([texts[j]])
                        all_vectors.extend(single_vector)
                        print(f"     단일 문서 처리: {j+1}/{len(texts)}")
                else:
                    raise e
        
        print(f"✅ 전체 {len(all_vectors)}개 벡터 생성 완료")
        
        # 데이터 준비
        product_ids = []
        product_names = []
        chunk_types = []
        sources = []
        contents = []
        
        for i, text in enumerate(texts):
            metadata = metadatas[i]
            
            # 메타데이터 추출
            product_id = metadata.get('product_id', 0)
            product_name = metadata.get('product_name', '')
            chunk_type = metadata.get('chunk_type', 'unknown')
            source = metadata.get('source', '')

            # 데이터 추가
            product_ids.append(product_id)
            product_names.append(product_name)
            chunk_types.append(chunk_type)
            sources.append(source)
            contents.append(text)
        
        # Milvus에 삽입할 데이터 구성
        data = [
            all_vectors,  # 배치로 생성된 전체 벡터
            product_ids,
            product_names,
            chunk_types,
            sources,
            contents
        ]

        # 컬렉션 로드 (검색을 위해 필요)
        self.collection.load()
        
        # 데이터 삽입
        mr = self.collection.insert(data)
        print(f"✅ {len(texts)}개 문서가 성공적으로 삽입되었습니다.")
        
        # 데이터 플러시 (영구 저장)
        self.collection.flush()
        print("✅ 데이터가 영구 저장되었습니다.")
        
        return mr.primary_keys  

    def add_documents(self, documents: List[Document], **kwargs) -> List[str]:
        """Document 객체 리스트를 벡터 스토어에 추가"""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.add_texts(texts, metadatas, **kwargs)

    def similarity_search(self, query: str, k: int = 4, **kwargs) -> List[Document]:
        """유사한 문서 검색 (LangChain 인터페이스)"""
        # 먼저 컬렉션의 총 문서 수 확인
        self.collection.load()
        total_docs = self.collection.num_entities
        print(f"\n📊 컬렉션 총 문서 수: {total_docs}")
        print(f"📊 요청된 k 값: {k}")
        
        # 실제 k 값 조정 (총 문서 수보다 클 수 없음)
        actual_k = min(k, total_docs)
        print(f"📊 실제 검색할 k 값: {actual_k}")
        
        if total_docs == 0:
            print("⚠️ 컬렉션에 문서가 없습니다!")
            return []
        
        # 쿼리 임베딩 생성
        print(f"\n🔍 쿼리 임베딩 생성: '{query}'")
        query_vector = self.embedding_model.embed_query(query)
        print(f"📏 쿼리 벡터 차원: {len(query_vector)}")

        # 인덱스 정보 확인
        try:
            vector_index = self.collection.indexes[0]
            index_type = vector_index.params.get("index_type")
            metric_type = vector_index.params.get("metric_type")

            if index_type == 'HNSW':
                params = {"ef": 64}
            elif index_type in ["IVF_FLAT", "IVF_SQ8", "IVF_PQ"]:
                params = {"nprobe": 10}
            else:
                params = {}
        except:
            # 기본값 사용
            metric_type = self.metric_type
            index_type = self.index_type
            params = {}

        # 검색 파라미터
        print(f"\n🔧 검색 파라미터:")
        print(f"   - metric_type: {metric_type}")
        print(f"   - index_type: {index_type}")
        print(f"   - params: {params}")
        print(f"   - limit: {actual_k}")
        
        search_params = {"metric_type": metric_type, "params": params}
        
        # 검색 실행
        print(f"\n🔍 벡터 검색 실행 중...")
        try:
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=actual_k,
                output_fields=["product_id", "product_name", "chunk_type", "source", "content"]
            )
            
            print(f"✅ 검색 완료!")
            print(f"📊 검색 결과 개수: {len(results[0]) if results else 0}")
            
            # 각 결과의 상세 정보 출력
            if results and len(results[0]) > 0:
                for i, hit in enumerate(results[0]):
                    print(f"   결과 {i+1}: score={hit.score:.4f}, product_id={hit.entity.get('product_id')}")
                    print(f"          제품명: {hit.entity.get('product_name', 'N/A')}")
                    print(f"          청크타입: {hit.entity.get('chunk_type', 'N/A')}")
            
        except Exception as e:
            print(f"❌ 검색 중 오류: {e}")
            return []
        
        # LangChain Document 형식으로 변환
        print(f"\n🔄 LangChain Document 형식으로 변환 중...")
        docs = []
        for hits in results:
            for hit in hits:
                doc = Document(
                    page_content=hit.entity.get("content"),
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
        
        print(f"✅ {len(docs)}개 문서를 LangChain Document로 변환 완료")
        return docs
    
    def similarity_search_with_score(self, query: str, k: int = 4, **kwargs) -> List[tuple]:
        """유사도 점수와 함께 검색"""
        docs = self.similarity_search(query, k, **kwargs)
        return [(doc, doc.metadata.get('score', 0.0)) for doc in docs]

    @classmethod
    def from_texts(cls, texts: List[str], embedding_model: HuggingFaceEmbeddings, metadatas: Optional[List[dict]] = None, **kwargs):
        """텍스트 리스트로부터 벡터 스토어 생성"""
        vector_store = cls(embedding_model=embedding_model, **kwargs)
        vector_store.add_texts(texts, metadatas)
        print("✅ 벡터 스토어 생성 완료")
        return vector_store

    @classmethod
    def from_documents(cls, documents: List[Document], embedding_model: HuggingFaceEmbeddings, **kwargs):
        """Document 리스트로부터 벡터 스토어 생성"""
        vector_store = cls(embedding_model=embedding_model, **kwargs)
        vector_store.add_documents(documents)
        print("✅ 벡터 스토어 생성 완료")
        return vector_store