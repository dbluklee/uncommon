"""
LLM 클라이언트 모듈
Ollama Gemma3 모델을 사용한 응답 생성
"""

import os
import logging
import requests
import json
from typing import AsyncGenerator, Optional, List, Dict, Any
import aiohttp
import asyncio
import base64
from PIL import Image
import io

logger = logging.getLogger(__name__)

class LLMClient:
    """Ollama LLM 클라이언트"""
    
    def __init__(self):
        """LLM 클라이언트 초기화"""
        self.ollama_host = os.environ["OLLAMA_HOST"]
        self.ollama_port = os.environ["OLLAMA_PORT"]
        self.model_name = os.environ["OLLAMA_MODEL"]
        # Ensure we use the full model name
        if self.model_name == "gemma3":
            self.model_name = "gemma3:27b-it-q4_K_M"
        
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
                
                logger.info(f"✅ Ollama 연결 성공! 설정 모델: {self.model_name}")
                if any(self.model_name in name for name in model_names):
                    logger.info(f"✅ 모델 '{self.model_name}' 확인됨")
                else:
                    logger.warning(f"⚠️ 모델 '{self.model_name}'을 찾을 수 없습니다. 사용 가능한 모델: {model_names}")
                    # 사용 가능한 gemma3 모델 자동 선택
                    gemma3_models = [name for name in model_names if 'gemma3' in name.lower()]
                    if gemma3_models:
                        self.model_name = gemma3_models[0]
                        logger.info(f"🔄 자동 선택된 모델: {self.model_name}")
            else:
                logger.warning(f"⚠️ Ollama 서버 응답 오류: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ollama 연결 실패: {str(e)}")
            logger.info("로컬 Ollama를 사용하거나 원격 서버 설정을 확인하세요")
    
    def _build_prompt(self, query: str, context: str, has_image: bool = False) -> str:
        """프롬프트 구성"""
        if has_image:
            prompt = f"""당신은 UNCOMMON 안경 브랜드의 제품 전문가입니다. 
사용자가 업로드한 이미지와 제품 정보를 함께 분석해서 질문에 답변해주세요.

제품 정보:
{context}

고객 질문: {query}

이미지를 자세히 분석하고, 제품 정보와 함께 고려해서 정확하고 도움이 되는 답변을 해주세요.

답변:"""
        else:
            prompt = f"""당신은 UNCOMMON 안경 브랜드의 제품 전문가입니다. 
제공된 제품 정보를 바탕으로 고객의 질문에 친절하고 정확하게 답변해주세요.

제품 정보:
{context}

고객 질문: {query}

답변:"""
        return prompt
    
    def _encode_image(self, image_data: bytes) -> str:
        """이미지를 base64로 인코딩"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def _process_image(self, image_data: bytes, max_size: tuple = (1024, 1024)) -> bytes:
        """이미지 크기 조정 및 최적화"""
        try:
            # PIL Image로 변환
            image = Image.open(io.BytesIO(image_data))
            
            # RGBA -> RGB 변환 (JPEG 호환성)
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'LA':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1])
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 크기 조정
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # JPEG로 압축
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"이미지 처리 실패: {str(e)}")
            return image_data  # 원본 반환
    
    async def generate(self, query: str, context: str, temperature: float = 0.7, image_data: Optional[bytes] = None) -> str:
        """
        동기식 응답 생성 (이미지 지원)
        
        Args:
            query: 사용자 질문
            context: 검색된 컨텍스트
            temperature: 생성 온도
            image_data: 이미지 바이트 데이터 (선택사항)
            
        Returns:
            생성된 응답 텍스트
        """
        try:
            # 이미지가 있는 경우 채팅 API 사용
            if image_data:
                return await self._generate_with_image(query, context, temperature, image_data, stream=False)
            
            # 텍스트만 있는 경우 기존 방식
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
    
    async def _generate_with_image(self, query: str, context: str, temperature: float, image_data: bytes, stream: bool = False) -> str:
        """
        이미지를 포함한 응답 생성
        
        Args:
            query: 사용자 질문
            context: 검색된 컨텍스트
            temperature: 생성 온도
            image_data: 이미지 바이트 데이터
            stream: 스트리밍 여부
            
        Returns:
            생성된 응답 텍스트
        """
        try:
            # 이미지 처리 및 인코딩
            processed_image = self._process_image(image_data)
            image_b64 = self._encode_image(processed_image)
            
            # 채팅 메시지 구성
            messages = [
                {
                    "role": "user",
                    "content": self._build_prompt(query, context, has_image=True),
                    "images": [image_b64]
                }
            ]
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.chat_url, json=payload) as response:
                    if response.status == 200:
                        if stream:
                            # 스트리밍 처리는 별도 메소드에서
                            return ""
                        else:
                            result = await response.json()
                            return result.get("message", {}).get("content", "이미지 분석 응답을 생성할 수 없습니다.")
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama 이미지 API 오류: {response.status} - {error_text}")
                        return "이미지 분석 중 오류가 발생했습니다."
                        
        except Exception as e:
            logger.error(f"이미지 분석 실패: {str(e)}")
            return f"이미지 분석 중 오류가 발생했습니다: {str(e)}"
    
    async def stream_generate(self, query: str, context: str, temperature: float = 0.7, image_data: Optional[bytes] = None) -> AsyncGenerator[str, None]:
        """
        스트리밍 응답 생성 (이미지 지원)
        
        Args:
            query: 사용자 질문
            context: 검색된 컨텍스트
            temperature: 생성 온도
            image_data: 이미지 바이트 데이터 (선택사항)
            
        Yields:
            생성된 텍스트 청크
        """
        try:
            # 이미지가 있는 경우 멀티모달 스트리밍
            if image_data:
                async for chunk in self._stream_with_image(query, context, temperature, image_data):
                    yield chunk
                return
            
            # 텍스트만 있는 경우 기존 방식
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
    
    async def _stream_with_image(self, query: str, context: str, temperature: float, image_data: bytes) -> AsyncGenerator[str, None]:
        """
        이미지를 포함한 스트리밍 응답 생성
        
        Args:
            query: 사용자 질문
            context: 검색된 컨텍스트
            temperature: 생성 온도
            image_data: 이미지 바이트 데이터
            
        Yields:
            생성된 텍스트 청크
        """
        try:
            # 이미지 처리 및 인코딩
            processed_image = self._process_image(image_data)
            image_b64 = self._encode_image(processed_image)
            
            # 채팅 메시지 구성
            messages = [
                {
                    "role": "user",
                    "content": self._build_prompt(query, context, has_image=True),
                    "images": [image_b64]
                }
            ]
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.chat_url, json=payload) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                try:
                                    # NDJSON 파싱
                                    data = json.loads(line.decode('utf-8'))
                                    if "message" in data and "content" in data["message"]:
                                        yield data["message"]["content"]
                                    
                                    # 종료 확인
                                    if data.get("done", False):
                                        break
                                        
                                except json.JSONDecodeError:
                                    continue
                                except Exception as e:
                                    logger.error(f"이미지 스트리밍 파싱 오류: {str(e)}")
                                    continue
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama 이미지 스트리밍 오류: {response.status} - {error_text}")
                        yield "이미지 스트리밍 응답 생성 중 오류가 발생했습니다."
                        
        except Exception as e:
            logger.error(f"이미지 스트리밍 생성 실패: {str(e)}")
            yield f"이미지 스트리밍 오류: {str(e)}"
    
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