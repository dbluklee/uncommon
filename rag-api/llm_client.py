"""
LLM 클라이언트 모듈
Ollama Gemma3 모델을 사용한 응답 생성
"""

import os
import logging
import requests
import json
from typing import AsyncGenerator, Optional
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class LLMClient:
    """Ollama LLM 클라이언트"""
    
    def __init__(self):
        """LLM 클라이언트 초기화"""
        self.ollama_host = os.getenv("OLLAMA_HOST", "localhost")
        self.ollama_port = os.getenv("OLLAMA_PORT", "11434")
        self.model_name = os.getenv("OLLAMA_MODEL", "gemma3")
        
        # API 엔드포인트
        self.base_url = f"http://{self.ollama_host}:{self.ollama_port}"
        self.generate_url = f"{self.base_url}/api/generate"
        self.chat_url = f"{self.base_url}/api/chat"
        
        # 연결 테스트
        self._test_connection()
    
    def _test_connection(self):
        """Ollama 서버 연결 테스트"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                if any(self.model_name in name for name in model_names):
                    logger.info(f"✅ Ollama 연결 성공! 모델: {self.model_name}")
                else:
                    logger.warning(f"⚠️ 모델 '{self.model_name}'을 찾을 수 없습니다. 사용 가능한 모델: {model_names}")
            else:
                logger.warning(f"⚠️ Ollama 서버 응답 오류: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ollama 연결 실패: {str(e)}")
            logger.info("로컬 Ollama를 사용하거나 원격 서버 설정을 확인하세요")
    
    def _build_prompt(self, query: str, context: str) -> str:
        """프롬프트 구성"""
        prompt = f"""당신은 UNCOMMON 안경 브랜드의 제품 전문가입니다. 
제공된 제품 정보를 바탕으로 고객의 질문에 친절하고 정확하게 답변해주세요.

제품 정보:
{context}

고객 질문: {query}

답변:"""
        return prompt
    
    async def generate(self, query: str, context: str, temperature: float = 0.7) -> str:
        """
        동기식 응답 생성
        
        Args:
            query: 사용자 질문
            context: 검색된 컨텍스트
            temperature: 생성 온도
            
        Returns:
            생성된 응답 텍스트
        """
        try:
            prompt = self._build_prompt(query, context)
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "temperature": temperature,
                "stream": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.generate_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "응답을 생성할 수 없습니다.")
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API 오류: {response.status} - {error_text}")
                        return "죄송합니다. 응답 생성 중 오류가 발생했습니다."
                        
        except Exception as e:
            logger.error(f"응답 생성 실패: {str(e)}")
            return f"응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    async def stream_generate(self, query: str, context: str, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """
        스트리밍 응답 생성
        
        Args:
            query: 사용자 질문
            context: 검색된 컨텍스트
            temperature: 생성 온도
            
        Yields:
            생성된 텍스트 청크
        """
        try:
            prompt = self._build_prompt(query, context)
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "temperature": temperature,
                "stream": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.generate_url, json=payload) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                try:
                                    # NDJSON 파싱
                                    data = json.loads(line.decode('utf-8'))
                                    if "response" in data:
                                        yield data["response"]
                                    
                                    # 종료 확인
                                    if data.get("done", False):
                                        break
                                        
                                except json.JSONDecodeError:
                                    continue
                                except Exception as e:
                                    logger.error(f"스트리밍 파싱 오류: {str(e)}")
                                    continue
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama 스트리밍 오류: {response.status} - {error_text}")
                        yield "스트리밍 응답 생성 중 오류가 발생했습니다."
                        
        except Exception as e:
            logger.error(f"스트리밍 생성 실패: {str(e)}")
            yield f"스트리밍 오류: {str(e)}"
    
    async def chat(self, messages: list, temperature: float = 0.7) -> str:
        """
        채팅 형식 응답 생성
        
        Args:
            messages: 대화 메시지 리스트
            temperature: 생성 온도
            
        Returns:
            생성된 응답
        """
        try:
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.chat_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("message", {}).get("content", "응답을 생성할 수 없습니다.")
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama 채팅 오류: {response.status} - {error_text}")
                        return "채팅 응답 생성 중 오류가 발생했습니다."
                        
        except Exception as e:
            logger.error(f"채팅 생성 실패: {str(e)}")
            return f"채팅 오류: {str(e)}"
    
    def get_model_info(self) -> dict:
        """모델 정보 반환"""
        return {
            "model_name": self.model_name,
            "host": self.ollama_host,
            "port": self.ollama_port,
            "base_url": self.base_url
        }