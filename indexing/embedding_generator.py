"""
BGE-M3 임베딩 생성 모듈 - 안정화 버전
sentence-transformers를 직접 사용한 BGE-M3 모델
"""

import torch
from sentence_transformers import SentenceTransformer
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any
import logging
import numpy as np

logger = logging.getLogger(__name__)

def download_model_automatically(model_path: str, model_name: str = "BAAI/bge-m3") -> bool:
    """자동으로 임베딩 모델을 다운로드합니다."""
    try:
        print(f"🚀 자동 모델 다운로드 시작...")
        print(f"   모델: {model_name}")
        print(f"   저장 위치: {model_path}")
        
        # 필요한 디렉토리 생성
        Path(model_path).mkdir(parents=True, exist_ok=True)
        
        # HuggingFace Hub 라이브러리로 직접 다운로드
        try:
            from huggingface_hub import snapshot_download
            print("📥 HuggingFace Hub에서 모델 다운로드 중...")
            print("   ⚠️ 대용량 파일입니다. 시간이 오래 걸릴 수 있습니다.")
            
            downloaded_path = snapshot_download(
                repo_id=model_name,
                local_dir=model_path,
                local_dir_use_symlinks=False,
                resume_download=True
            )
            
            print(f"✅ 모델 다운로드 완료: {downloaded_path}")
            return True
            
        except ImportError:
            print("❌ huggingface_hub가 설치되지 않았습니다.")
            print("   pip install huggingface_hub를 실행하세요.")
            return False
        except Exception as e:
            print(f"❌ 모델 다운로드 실패: {e}")
            return False
            
    except Exception as e:
        print(f"❌ 자동 다운로드 중 오류: {e}")
        return False

def verify_model_files(model_path: str) -> bool:
    """모델 파일이 완전히 다운로드되었는지 확인합니다."""
    required_files = ["config.json"]
    optional_files = ["pytorch_model.bin", "model.safetensors"]
    
    # 필수 파일 확인
    for file in required_files:
        if not Path(model_path + "/" + file).exists():
            return False
    
    # 모델 파일 중 하나는 있어야 함
    has_model_file = any(Path(model_path + "/" + file).exists() for file in optional_files)
    if not has_model_file:
        return False
    
    return True

def get_bge_m3_model():
    """
    BGE-M3 임베딩 모델을 로드합니다.
    로컬 모델 우선, 없으면 자동으로 다운로드
    USE_CUDA 환경변수에 따라 CPU/GPU를 선택합니다.
    """
    
    # USE_CUDA 환경변수 확인
    use_cuda = os.environ['USE_CUDA'].lower() == 'true'
    
    # 로컬 모델 경로 설정
    local_model_path = "/app/models/bge-m3"
    huggingface_model_name = 'BAAI/bge-m3'
    
    # 로컬 모델 존재 여부 확인
    local_model_exists = verify_model_files(local_model_path)
    
    # 모델 선택 로직
    if local_model_exists:
        print(f"🎯 로컬 모델 발견: {local_model_path}")
        model_name = local_model_path
        
        # 로컬 모델 파일 정보 출력
        try:
            model_files = list(Path(local_model_path).glob("*"))
            total_size = sum(f.stat().st_size for f in model_files if f.is_file()) / (1024*1024*1024)
            print(f"📏 로컬 모델 크기: {total_size:.1f}GB")
            print(f"📋 모델 파일 수: {len([f for f in model_files if f.is_file()])}개")
        except Exception as e:
            print(f"⚠️ 모델 정보 확인 중 오류: {e}")
            
    else:
        print(f"⚠️ 로컬 모델 없음: {local_model_path}")
        print(f"🌐 모델 소스: {huggingface_model_name}")
        model_name = huggingface_model_name
    
    # USE_CUDA가 false면 CUDA_VISIBLE_DEVICES를 빈 문자열로 설정하여 GPU 비활성화
    if not use_cuda:
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        print("🔧 USE_CUDA=false - GPU 비활성화, CPU 모드로 전환")
        device = 'cpu'
    elif torch.cuda.is_available():
        device = 'cuda'
    else:
        print("⚠️ CUDA 사용할 수 없음, CPU 모드로 전환")
        device = 'cpu'
    
    print(f"🔧 임베딩 모델 디바이스: {device}")
    print(f"📁 모델 소스: {'로컬 파일' if model_name == local_model_path else 'HuggingFace Hub'}")
    
    model_kwargs = {'device': device}
    encode_kwargs = {'normalize_embeddings': True}
    
    try:
        print(f"⏳ 임베딩 모델 로딩 중...")
        
        # sentence-transformers를 직접 사용
        model = SentenceTransformer(model_name, device=device)
        
        # 로딩 성공 후 간단한 테스트
        print(f"🧪 모델 테스트 중...")
        test_embedding = model.encode("test", convert_to_numpy=True)
        embedding_dim = len(test_embedding)
        
        print(f"✅ 임베딩 모델 로딩 완료!")
        print(f"   📏 임베딩 차원: {embedding_dim}")
        print(f"   🎯 디바이스: {device}")
        print(f"   📁 모델 경로: {model_name}")
        
        # langchain 호환을 위한 래퍼 클래스
        class SentenceTransformerWrapper:
            def __init__(self, model):
                self.model = model
                
            def embed_query(self, text: str) -> List[float]:
                """단일 쿼리 임베딩"""
                embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
                return embedding.tolist()
                
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                """여러 문서 임베딩"""
                embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings.tolist()
        
        return SentenceTransformerWrapper(model)
        
    except Exception as e:
        error_msg = f"❌ 임베딩 모델 로딩 실패: {e}\n"
        
        if model_name == local_model_path:
            error_msg += "해결방법:\n"
            error_msg += "1. 로컬 모델 파일 손상 확인\n"
            error_msg += "2. 모델 재다운로드\n"
            error_msg += "3. USE_CUDA=false로 설정하여 CPU 모드 시도\n"
            error_msg += "4. HuggingFace Hub 모드로 전환 (로컬 모델 삭제)"
        else:
            error_msg += "해결방법:\n"
            error_msg += "1. 인터넷 연결 확인 (HuggingFace 모델 다운로드)\n"
            error_msg += "2. 로컬 모델 다운로드\n"
            error_msg += "3. 디스크 공간 확인\n"
            error_msg += "4. USE_CUDA=false로 설정하여 CPU 모드 시도"
        
        raise RuntimeError(error_msg)