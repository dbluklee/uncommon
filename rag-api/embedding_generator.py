"""
임베딩 생성 모듈
BGE-M3 모델을 사용한 쿼리 임베딩 생성
"""

import os
import logging
from typing import List, Union
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """BGE-M3 임베딩 생성기"""
    
    def __init__(self):
        """임베딩 모델 초기화"""
        self.model_name = os.environ["EMBEDDING_MODEL"]
        self.use_cuda = os.environ["USE_CUDA"].lower() == "true"
        
        # 디바이스 설정
        if self.use_cuda and torch.cuda.is_available():
            self.device = f"cuda:{os.environ['CUDA_DEVICE']}"
            logger.info(f"🎮 CUDA 사용: {self.device}")
        else:
            self.device = "cpu"
            logger.info("💻 CPU 모드로 실행")
        
        # 모델 로딩
        logger.info(f"📥 임베딩 모델 로딩: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            
            # 모델 테스트
            test_embedding = self.model.encode("test", convert_to_numpy=True)
            self.dimension = len(test_embedding)
            
            logger.info(f"✅ 임베딩 모델 로딩 완료 (차원: {self.dimension})")
            
        except Exception as e:
            logger.error(f"❌ 모델 로딩 실패: {str(e)}")
            raise
    
    def generate_embedding(self, text: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        텍스트를 임베딩 벡터로 변환
        
        Args:
            text: 임베딩할 텍스트 (문자열 또는 리스트)
            normalize: 벡터 정규화 여부
            
        Returns:
            numpy array 형태의 임베딩 벡터
        """
        try:
            # 단일 문자열을 리스트로 변환
            if isinstance(text, str):
                text = [text]
            
            # 임베딩 생성
            embeddings = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            
            # 단일 텍스트인 경우 1차원 배열 반환
            if len(text) == 1:
                return embeddings[0]
            
            return embeddings
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {str(e)}")
            raise
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        검색 쿼리용 임베딩 생성
        
        Args:
            query: 검색 쿼리 문자열
            
        Returns:
            리스트 형태의 임베딩 벡터
        """
        try:
            # 쿼리 전처리 (BGE-M3는 쿼리에 특별한 프리픽스 필요 없음)
            processed_query = query.strip()
            
            # 임베딩 생성
            embedding = self.generate_embedding(processed_query, normalize=True)
            
            # 리스트로 변환하여 반환
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"쿼리 임베딩 생성 실패: {str(e)}")
            raise
    
    def batch_generate_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        배치 단위로 임베딩 생성
        
        Args:
            texts: 임베딩할 텍스트 리스트
            batch_size: 배치 크기
            
        Returns:
            임베딩 벡터 리스트
        """
        all_embeddings = []
        
        try:
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.generate_embedding(batch, normalize=True)
                
                # numpy array를 리스트로 변환
                for embedding in batch_embeddings:
                    all_embeddings.append(embedding.tolist())
                
                logger.info(f"배치 {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} 처리 완료")
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"배치 임베딩 생성 실패: {str(e)}")
            raise
    
    def get_dimension(self) -> int:
        """임베딩 차원 반환"""
        return self.dimension
    
    def get_model_info(self) -> dict:
        """모델 정보 반환"""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "device": self.device,
            "cuda_available": torch.cuda.is_available()
        }