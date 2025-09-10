"""
Router LLM Client for Conditional RAG
질문이 RAG가 필요한지 판단하는 LLM 클라이언트
"""

import os
import logging
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class RouterLLMClient:
    """RAG 필요성 판단을 위한 라우터 LLM 클라이언트"""
    
    def __init__(self):
        self.host = os.environ["ROUTER_LLM_HOST"]
        self.port = os.environ["ROUTER_LLM_PORT"] 
        self.model = os.environ["ROUTER_LLM_MODEL"]
        self.base_url = f"http://{self.host}:{self.port}"
        
        logger.info(f"🤖 Router LLM 초기화: {self.base_url} (모델: {self.model})")
        
        # 연결 테스트
        self._test_connection()
    
    def _test_connection(self):
        """Ollama 서버 연결 테스트"""
        try:
            with httpx.Client(timeout=10.0) as client:
                # 서버 상태 확인
                response = client.get(f"{self.base_url}/api/version")
                if response.status_code == 200:
                    logger.info("✅ Router LLM 서버 연결 성공!")
                else:
                    logger.warning(f"⚠️ Router LLM 서버 응답 오류: {response.status_code}")
                    
                # 모델 존재 확인
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m["name"] for m in models]
                    if self.model in model_names:
                        logger.info(f"✅ Router 모델 '{self.model}' 확인됨")
                    else:
                        logger.warning(f"⚠️ Router 모델 '{self.model}'를 찾을 수 없음. 사용 가능 모델: {model_names}")
                        
        except Exception as e:
            logger.error(f"❌ Router LLM 연결 실패: {str(e)}")
            raise
    
    async def should_use_rag(self, query: str) -> bool:
        """
        질문이 RAG가 필요한지 판단
        
        Args:
            query: 사용자 질문
            
        Returns:
            bool: RAG 사용 여부 (True: 필요, False: 불필요)
        """
        try:
            logger.info(f"🔍 Router 판단 요청: {query[:50]}...")
            
            # 라우터 프롬프트 구성
            router_prompt = f"""다음 질문을 분석해서 UNCOMMON 안경 제품 정보가 필요한지 판단해주세요.

질문: "{query}"

판단 기준:
- 제품 정보 필요: 안경, 선글라스, 제품명, 가격, 색상, 재질, 사이즈, 브랜드(UNCOMMON), 구매, 추천 등
- 제품 정보 불필요: 일반 인사, 날씨, 뉴스, 일반 상식, 개인적 질문 등

답변: 제품정보필요 또는 제품정보불필요 중 하나만 답하세요."""

            # Ollama API 호출
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": router_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # 일관된 판단을 위해 낮은 온도
                            "num_predict": 10,   # 짧은 답변만 필요
                            "stop": ["\n", ".", ","]  # 답변을 짧게 제한
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("response", "").strip().lower()
                    
                    # 답변 분석
                    needs_rag = "제품정보필요" in answer and "제품정보불필요" not in answer
                    
                    logger.info(f"🎯 Router 판단 결과: {'RAG 필요' if needs_rag else 'RAG 불필요'} (답변: {answer})")
                    return needs_rag
                    
                else:
                    logger.error(f"❌ Router LLM API 오류: {response.status_code}")
                    # 기본값으로 RAG 사용 (안전한 선택)
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Router 판단 실패: {str(e)}")
            # 오류 시 기본값으로 RAG 사용 (안전한 선택)
            return True
    
    async def generate_direct_response(self, query: str, temperature: float = 0.7) -> str:
        """
        RAG 없이 직접 응답 생성
        
        Args:
            query: 사용자 질문
            temperature: 생성 온도
            
        Returns:
            str: 생성된 응답
        """
        try:
            logger.info(f"💬 Router LLM 직접 응답 생성: {query[:50]}...")
            
            # 직접 응답용 프롬프트
            direct_prompt = f"""당신은 친근하고 도움이 되는 AI 어시스턴트입니다.
사용자의 질문에 자연스럽고 도움이 되는 답변을 해주세요.

사용자 질문: {query}

답변:"""

            # Ollama API 호출
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": direct_prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": 200
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("response", "").strip()
                    
                    logger.info(f"✅ Router LLM 직접 응답 생성 완료 ({len(answer)}자)")
                    return answer
                    
                else:
                    logger.error(f"❌ Router LLM 직접 응답 API 오류: {response.status_code}")
                    return "죄송합니다. 현재 응답을 생성할 수 없습니다."
                    
        except Exception as e:
            logger.error(f"❌ Router LLM 직접 응답 생성 실패: {str(e)}")
            return "죄송합니다. 기술적 문제로 응답을 생성할 수 없습니다."
    
    async def stream_direct_response(self, query: str, temperature: float = 0.7):
        """
        RAG 없이 직접 스트리밍 응답 생성
        
        Args:
            query: 사용자 질문
            temperature: 생성 온도
            
        Yields:
            str: 스트리밍 응답 청크
        """
        try:
            logger.info(f"📡 Router LLM 스트리밍 응답 시작: {query[:50]}...")
            
            # 직접 응답용 프롬프트
            direct_prompt = f"""당신은 친근하고 도움이 되는 AI 어시스턴트입니다.
사용자의 질문에 자연스럽고 도움이 되는 답변을 해주세요.

사용자 질문: {query}

답변:"""

            # Ollama 스트리밍 API 호출
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": direct_prompt,
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                            "num_predict": 200
                        }
                    }
                ) as response:
                    
                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    import json
                                    chunk_data = json.loads(line)
                                    
                                    if "response" in chunk_data:
                                        chunk = chunk_data["response"]
                                        if chunk:
                                            yield chunk
                                            
                                    # 완료 체크
                                    if chunk_data.get("done", False):
                                        logger.info("✅ Router LLM 스트리밍 완료")
                                        break
                                        
                                except json.JSONDecodeError:
                                    continue
                                    
                    else:
                        logger.error(f"❌ Router LLM 스트리밍 API 오류: {response.status_code}")
                        yield "죄송합니다. 현재 응답을 생성할 수 없습니다."
                        
        except Exception as e:
            logger.error(f"❌ Router LLM 스트리밍 실패: {str(e)}")
            yield "죄송합니다. 기술적 문제로 응답을 생성할 수 없습니다."